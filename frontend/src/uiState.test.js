import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearStoredState, readStoredState, writeStoredState } from "./uiState";

describe("account-scoped UI state", () => {
  let values;

  beforeEach(() => {
    values = new Map();
    vi.stubGlobal("localStorage", {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, value),
      removeItem: (key) => values.delete(key)
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("restores a user's draft without exposing it to another account or the demo", () => {
    const draft = { form: { resume_text: "User A's private resume" }, selectedRun: "run-a" };
    writeStoredState(draft, "user-a");

    expect(readStoredState("user-a")).toEqual(draft);
    expect(readStoredState("user-b")).toEqual({});
    expect(readStoredState()).toEqual({});

    writeStoredState({ form: { notes: "User B's draft" } }, "user-b");
    expect(readStoredState("user-a")).toEqual(draft);
  });

  it("discards the old unscoped cache rather than assigning it to a signed-in user", () => {
    values.set("internlens.ui.state", JSON.stringify({ form: { resume_text: "Unknown owner" } }));

    expect(readStoredState("user-b")).toEqual({});
    expect(values.has("internlens.ui.state")).toBe(false);
  });

  it("clears the signed-out user's state while preserving another user's draft", () => {
    writeStoredState({ form: { resume_text: "A" } }, "user-a");
    writeStoredState({ form: { resume_text: "B" } }, "user-b");

    clearStoredState("user-a");

    expect(readStoredState("user-a")).toEqual({});
    expect(readStoredState("user-b")).toEqual({ form: { resume_text: "B" } });
  });

  it("keeps demo draft restoration available", () => {
    const draft = { form: { notes: "Local demo" }, recommendationFilter: "apply_now" };
    writeStoredState(draft);
    expect(readStoredState()).toEqual(draft);
  });

  it("works when browser storage is unavailable", () => {
    vi.stubGlobal("localStorage", {
      getItem: () => { throw new Error("Storage blocked"); },
      setItem: () => { throw new Error("Storage blocked"); },
      removeItem: () => { throw new Error("Storage blocked"); }
    });

    expect(readStoredState("user-a")).toEqual({});
    expect(() => writeStoredState({}, "user-a")).not.toThrow();
    expect(() => clearStoredState("user-a")).not.toThrow();
  });
});
