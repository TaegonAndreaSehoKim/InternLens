function createApiClient({ baseUrl, getAccessToken = null, onUnauthorized = null, fetchRequest = (...args) => fetch(...args) }) {
  return async function api(path, options = {}) {
    async function send(forceRefresh = false) {
      const headers = new Headers(options.headers);
      const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
      if (!isFormData && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
      if (getAccessToken) {
        const token = await getAccessToken({ forceRefresh });
        if (!token) {
          throw Object.assign(new Error("Your session has ended. Please log in again."), { status: 401 });
        }
        headers.set("Authorization", `Bearer ${token}`);
      }
      return fetchRequest(`${baseUrl}${path}`, { ...options, headers });
    }

    try {
      let response = await send();
      if (response.status === 401 && getAccessToken) {
        response = await send(true);
      }
      const body = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw Object.assign(new Error(body.detail ?? body.message ?? `Request failed: ${response.status}`), { status: response.status, data: body });
      }
      return body;
    } catch (error) {
      if (error.status === 401 && getAccessToken) {
        onUnauthorized?.();
      }
      throw error;
    }
  };
}

export { createApiClient };
