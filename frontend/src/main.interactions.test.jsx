// @vitest-environment jsdom

import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App, RecommendationPanel } from "./main.jsx";
import { readStoredState, writeStoredState } from "./uiState";

const candidate = {
  profile_id: "candidate", degree_level: "Bachelor's", major: "Computer Science", majors: ["Computer Science"],
  grad_date: "2027-05", preferred_roles: ["Software Engineering Intern"], preferred_locations: ["Remote"],
  target_industries: ["Technology"], extracted_skills: ["Python", "SQL", "AWS"], resume_text: "Private candidate resume",
  sponsorship_need: false, years_of_experience: 0, notes: "",
};
const job = {
  job_id: "job-1", company: "Acme", title: "Software Engineering Intern", location: "Remote",
  recommendation: "apply_now", fit_level: "strong", action_label: "Apply Now", score: 90,
  matched_skills: ["Python"], skill_gaps: [], blocking_issues: [], component_scores: {},
};
const run = { run_id: "run-1", results: [job] };

function workspaceApi({ readiness = "ready", failedAction = false, missingProfile = false } = {}) {
  let state = null;
  const dashboard = () => ({
    summary: { recommendation_run_count: 1, saved_jobs_count: Number(state === "saved"), applied_jobs_count: Number(state === "applied"), dismissed_jobs_count: Number(state === "dismissed") },
    recent_runs: [{ run_id: "run-1", created_at: "2026-10-05T00:00:00Z", returned_jobs: 1 }],
    saved_jobs: [], applied_jobs: [], dismissed_jobs: [], recommended_next_actions: [], activity: { activities: [] },
  });
  const fetchMock = vi.fn(async (url, options = {}) => {
    const path = new URL(url).pathname;
    let status = 200;
    let body;
    if (path === "/health") body = { status: "ok" };
    else if (path === "/ready") {
      status = readiness === "ready" ? 200 : 503;
      body = { status: readiness, active_job_count: readiness === "ready" ? 1 : 0, message: "Job sources need a refresh." };
    } else if (path === "/me/profile") {
      status = missingProfile && options.method !== "PUT" ? 404 : 200;
      body = status === 404 ? { detail: "Profile not found" } : options.body ? { ...candidate, ...JSON.parse(options.body) } : candidate;
    } else if (path === "/me/dashboard") body = dashboard();
    else if (path === "/me/recommend" || path === "/me/recommendations/run-1") body = { ...run, results: [{ ...job, user_job_state: state }] };
    else if (path === "/me/jobs/job-1/action") {
      if (failedAction) { status = 500; body = { detail: "Could not save this job" }; }
      else {
        const action = JSON.parse(options.body).action;
        state = { save: "saved", apply: "applied", dismiss: "dismissed", clear: null }[action];
        body = { job_state: state ? { state, source_run_id: "run-1" } : null };
      }
    } else throw new Error(`Unexpected API path: ${path}`);
    return { ok: status < 400, status, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function openWorkspace(options = {}) {
  const user = userEvent.setup();
  writeStoredState({ selectedRun: "run-1" }, "account-a");
  const fetchMock = workspaceApi(options);
  const rendered = render(<App accountUserId="account-a" />);
  await screen.findByRole("heading", { name: job.title });
  return { user, fetchMock, ...rendered };
}

beforeEach(() => localStorage.clear());
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("workspace interactions", () => {
  it("saves, applies, hides and restores a job through the API", async () => {
    const { user, fetchMock } = await openWorkspace();
    const card = within(screen.getByRole("heading", { name: job.title }).closest("article"));
    await user.click(card.getByRole("button", { name: "Save", exact: true }));
    await waitFor(() => expect(card.getByRole("button", { name: "Saved", exact: true }).disabled).toBe(true));
    await user.click(card.getByRole("button", { name: "Mark applied", exact: true }));
    await waitFor(() => expect(card.getByRole("button", { name: "Applied", exact: true }).disabled).toBe(true));
    await user.click(card.getByRole("button", { name: "Undo applied" }));
    await waitFor(() => expect(card.getByRole("button", { name: "Hide role" }).disabled).toBe(false));
    await user.click(card.getByRole("button", { name: "Hide role" }));
    await waitFor(() => expect(card.getByRole("button", { name: "Hidden", exact: true }).disabled).toBe(true));
    await user.click(card.getByRole("button", { name: "Show again" }));
    await waitFor(() => expect(card.getByRole("button", { name: "Save", exact: true }).disabled).toBe(false));
    const actions = fetchMock.mock.calls.filter(([url]) => url.endsWith("/action")).map(([, options]) => JSON.parse(options.body).action);
    expect(actions).toEqual(["save", "apply", "clear", "dismiss", "clear"]);
  });

  it("keeps a failed job action retryable without displaying a saved state", async () => {
    const { user } = await openWorkspace({ failedAction: true });
    const card = within(screen.getByRole("heading", { name: job.title }).closest("article"));
    await user.click(card.getByRole("button", { name: "Save", exact: true }));
    await screen.findByText("Could not save this job");
    expect(card.queryByRole("button", { name: "Saved", exact: true })).toBeNull();
    expect(card.getByRole("button", { name: "Save", exact: true }).disabled).toBe(false);
  });

  it("keeps historical results available while blocking new matches for expired data", async () => {
    const { user, fetchMock } = await openWorkspace({ readiness: "unavailable" });
    expect(screen.getByRole("button", { name: "Find matches" }).disabled).toBe(true);
    expect(screen.getByRole("heading", { name: job.title })).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Check again" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Check again" }).disabled).toBe(false));
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/ready"))).toHaveLength(2);
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/me/recommend"))).toBe(false);
  });

  it("remounts with the next account's draft instead of displaying the previous resume", async () => {
    workspaceApi({ missingProfile: true });
    writeStoredState({ form: { resume_text: "Account A private draft" } }, "account-a");
    const view = render(<App key="a" accountUserId="account-a" />);
    await screen.findByDisplayValue("Account A private draft");
    view.rerender(<App key="b" accountUserId="account-b" />);
    await waitFor(() => expect(screen.queryByDisplayValue("Account A private draft")).toBeNull());
    expect(readStoredState("account-b").form.resume_text).toBe("");
  });

  it("runs a new shortlist only after checking current job data", async () => {
    const { user, fetchMock } = await openWorkspace();
    await user.click(screen.getByRole("button", { name: "Find matches" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([url]) => url.endsWith("/me/recommend"))).toBe(true));
    const calls = fetchMock.mock.calls.map(([url]) => new URL(url).pathname);
    expect(calls.lastIndexOf("/ready")).toBeLessThan(calls.indexOf("/me/recommend"));
  });

  it("saves profile edits before allowing another recommendation run", async () => {
    const { user, fetchMock } = await openWorkspace();
    await user.click(screen.getByRole("button", { name: "Edit profile" }));
    await user.clear(screen.getByRole("textbox", { name: "Additional background" }));
    await user.type(screen.getByRole("textbox", { name: "Additional background" }), "Interested in distributed systems");
    expect(screen.getByRole("button", { name: "Save changes first" }).disabled).toBe(true);
    await user.click(screen.getAllByRole("button", { name: "Save profile" })[0]);
    await screen.findByText("Profile saved. Dashboard is ready.");
    expect(screen.getByRole("button", { name: "Find matches" }).disabled).toBe(false);
    const save = fetchMock.mock.calls.find(([url, options]) => url.endsWith("/me/profile") && options.method === "PUT");
    expect(JSON.parse(save[1].body).resume_text).toBe("Interested in distributed systems");
  });
});

describe("shortlist navigation", () => {
  it("searches results and navigates pages without losing the filter", async () => {
    const user = userEvent.setup();
    const jobs = Array.from({ length: 21 }, (_, index) => ({ ...job, score: 100 - index, job_id: `job-${index}`, title: `Engineering Intern ${index + 1}` }));
    render(<RecommendationPanel recommendations={{ results: jobs }} dashboardJobView="recommendations" selectedRun="run-1" filter="all" onFilterChange={() => {}} />);
    expect(screen.queryByRole("heading", { name: "Engineering Intern 21" })).toBeNull();
    await user.click(screen.getAllByRole("button", { name: "Next" })[0]);
    expect(screen.getByRole("heading", { name: "Engineering Intern 21" })).toBeTruthy();
    await user.type(screen.getByRole("textbox", { name: "Search" }), "Intern 3");
    expect(screen.getByRole("heading", { name: "Engineering Intern 3" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Engineering Intern 21" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Next" })).toBeNull();
  });
});
