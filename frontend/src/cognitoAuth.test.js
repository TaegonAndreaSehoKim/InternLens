import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchAuthSession, fetchUserAttributes, getCurrentUser } from "aws-amplify/auth";
import { currentCognitoAccessToken, currentCognitoSession } from "./cognitoAuth";
import { createApiClient } from "./apiClient";

vi.mock("aws-amplify/auth", () => ({
  confirmSignIn: vi.fn(),
  confirmSignUp: vi.fn(),
  fetchAuthSession: vi.fn(),
  fetchUserAttributes: vi.fn(),
  getCurrentUser: vi.fn(),
  resendSignUpCode: vi.fn(),
  signIn: vi.fn(),
  signOut: vi.fn(),
  signUp: vi.fn()
}));

const authSession = (userId, token) => ({
  tokens: { accessToken: { payload: { sub: userId }, toString: () => token } }
});

describe("Cognito session identity", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getCurrentUser.mockResolvedValue({ userId: "user-a", username: "username-a" });
    fetchUserAttributes.mockResolvedValue({ email: "a@example.com" });
    fetchAuthSession.mockResolvedValue(authSession("user-a", "token-a"));
  });

  it("restores the stable user identity without keeping a token snapshot in UI state", async () => {
    await expect(currentCognitoSession()).resolves.toEqual({ userId: "user-a", email: "a@example.com" });
  });

  it("uses the SDK session's current token on every call and supports forced refresh", async () => {
    fetchAuthSession
      .mockResolvedValueOnce(authSession("user-a", "token-a"))
      .mockResolvedValueOnce(authSession("user-a", "token-renewed"));

    await expect(currentCognitoAccessToken("user-a")).resolves.toBe("token-a");
    await expect(currentCognitoAccessToken("user-a", { forceRefresh: true })).resolves.toBe("token-renewed");
    expect(fetchAuthSession).toHaveBeenLastCalledWith({ forceRefresh: true });
  });

  it("rejects a token belonging to a different account", async () => {
    fetchAuthSession.mockResolvedValue(authSession("user-b", "token-b"));
    await expect(currentCognitoAccessToken("user-a")).rejects.toMatchObject({ status: 401 });
    await expect(currentCognitoSession()).rejects.toMatchObject({ status: 401 });
  });

  it("rejects a missing session rather than falling back to an unauthenticated request", async () => {
    fetchAuthSession.mockResolvedValue({});
    await expect(currentCognitoAccessToken("user-a")).rejects.toMatchObject({ status: 401 });
  });

  it("never retries a profile mutation using another account's refreshed token", async () => {
    fetchAuthSession
      .mockResolvedValueOnce(authSession("user-a", "token-a"))
      .mockResolvedValueOnce(authSession("user-b", "token-b"));
    const fetchRequest = vi.fn().mockResolvedValue({ status: 401 });
    const onUnauthorized = vi.fn();
    const api = createApiClient({
      baseUrl: "",
      getAccessToken: (options) => currentCognitoAccessToken("user-a", options),
      onUnauthorized,
      fetchRequest
    });

    await expect(api("/me/profile", { method: "PUT", body: "{}" })).rejects.toMatchObject({ status: 401 });
    expect(fetchRequest).toHaveBeenCalledTimes(1);
    expect(fetchRequest.mock.calls[0][1].headers.get("Authorization")).toBe("Bearer token-a");
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });
});
