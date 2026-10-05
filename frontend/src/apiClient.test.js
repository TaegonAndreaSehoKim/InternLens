import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "./apiClient";

const jsonResponse = (status, body) => ({ status, ok: status < 400, json: async () => body });

describe("API authentication", () => {
  it("retrieves a current token for each request without dropping custom headers", async () => {
    const getAccessToken = vi.fn().mockResolvedValueOnce("first-token").mockResolvedValueOnce("renewed-token");
    const fetchRequest = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }));
    const api = createApiClient({ baseUrl: "https://api.example", getAccessToken, fetchRequest });

    await api("/me/profile", { headers: { "X-Request-Id": "review" } });
    await api("/me/dashboard");

    expect(fetchRequest.mock.calls[0][1].headers.get("Authorization")).toBe("Bearer first-token");
    expect(fetchRequest.mock.calls[0][1].headers.get("X-Request-Id")).toBe("review");
    expect(fetchRequest.mock.calls[1][1].headers.get("Authorization")).toBe("Bearer renewed-token");
    expect(getAccessToken).toHaveBeenCalledTimes(2);
  });

  it("refreshes and retries an unauthorized request once, preserving the mutation body", async () => {
    const getAccessToken = vi.fn().mockResolvedValueOnce("stale-token").mockResolvedValueOnce("fresh-token");
    const fetchRequest = vi.fn()
      .mockResolvedValueOnce(jsonResponse(401, { detail: "Expired" }))
      .mockResolvedValueOnce(jsonResponse(200, { state: "saved" }));
    const onUnauthorized = vi.fn();
    const api = createApiClient({ baseUrl: "", getAccessToken, fetchRequest, onUnauthorized });
    const body = JSON.stringify({ action: "save" });

    await expect(api("/me/jobs/job-a/action", { method: "POST", body })).resolves.toEqual({ state: "saved" });

    expect(getAccessToken).toHaveBeenNthCalledWith(2, { forceRefresh: true });
    expect(fetchRequest.mock.calls[1][1].headers.get("Authorization")).toBe("Bearer fresh-token");
    expect(fetchRequest.mock.calls[1][1].body).toBe(body);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("ends the UI session after a second 401 instead of retrying indefinitely", async () => {
    const getAccessToken = vi.fn().mockResolvedValue("token");
    const fetchRequest = vi.fn().mockResolvedValue(jsonResponse(401, { detail: "Invalid token" }));
    const onUnauthorized = vi.fn();
    const api = createApiClient({ baseUrl: "", getAccessToken, fetchRequest, onUnauthorized });

    await expect(api("/me/profile")).rejects.toMatchObject({ status: 401 });
    expect(fetchRequest).toHaveBeenCalledTimes(2);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("does not send an authenticated request when its session has ended or changed", async () => {
    const getAccessToken = vi.fn().mockRejectedValue(Object.assign(new Error("Session changed"), { status: 401 }));
    const fetchRequest = vi.fn();
    const onUnauthorized = vi.fn();
    const api = createApiClient({ baseUrl: "", getAccessToken, fetchRequest, onUnauthorized });

    await expect(api("/me/profile", { method: "PUT", body: "{}" })).rejects.toMatchObject({ status: 401 });
    expect(fetchRequest).not.toHaveBeenCalled();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("preserves multipart upload boundaries", async () => {
    const fetchRequest = vi.fn().mockResolvedValue(jsonResponse(200, {}));
    const api = createApiClient({ baseUrl: "", fetchRequest });
    const body = new FormData();
    body.append("file", new Blob(["resume"]), "resume.txt");

    await api("/me/profile/resume", { method: "POST", body });
    expect(fetchRequest.mock.calls[0][1].headers.has("Content-Type")).toBe(false);
    expect(fetchRequest.mock.calls[0][1].body).toBe(body);
  });

  it("keeps dev requests unauthenticated and does not retry server failures", async () => {
    const fetchRequest = vi.fn().mockResolvedValue(jsonResponse(500, { detail: "Server error" }));
    const api = createApiClient({ baseUrl: "", fetchRequest });

    await expect(api("/me/profile")).rejects.toMatchObject({ status: 500 });
    expect(fetchRequest).toHaveBeenCalledTimes(1);
    expect(fetchRequest.mock.calls[0][1].headers.has("Authorization")).toBe(false);
  });
});
