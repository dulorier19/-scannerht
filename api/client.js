const { env } = require("../config/env");

async function apiRequest(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), env.apiFetchTimeoutMs);

  let response;

  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(env.internalApiKey
          ? { "X-Internal-API-Key": env.internalApiKey }
          : {}),
        ...(options.headers || {}),
      },
    });
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API request failed (${response.status}): ${errorBody}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

module.exports = {
  apiRequest,
};
