const LEGACY_STORAGE_KEY = "internlens.ui.state";
const LOCAL_USER_ID = "local_user";

function storageKey(userId) {
  return `${LEGACY_STORAGE_KEY}.v2:${encodeURIComponent(userId)}`;
}

function readStoredState(userId = LOCAL_USER_ID) {
  try {
    // The shared legacy cache has no trustworthy account owner.
    globalThis.localStorage?.removeItem(LEGACY_STORAGE_KEY);
    const state = JSON.parse(globalThis.localStorage?.getItem(storageKey(userId)) ?? "null");
    return state && typeof state === "object" && !Array.isArray(state) ? state : {};
  } catch {
    return {};
  }
}

function writeStoredState(state, userId = LOCAL_USER_ID) {
  try {
    globalThis.localStorage?.setItem(storageKey(userId), JSON.stringify(state));
  } catch {
    // Browser storage can be unavailable in private or restricted sessions.
  }
}

function clearStoredState(userId) {
  try {
    globalThis.localStorage?.removeItem(storageKey(userId));
    globalThis.localStorage?.removeItem(LEGACY_STORAGE_KEY);
  } catch {
    // Signing out must still work when browser storage is unavailable.
  }
}

export { LOCAL_USER_ID, clearStoredState, readStoredState, writeStoredState };
