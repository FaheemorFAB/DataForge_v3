export async function apiFetch(endpoint: string, options: RequestInit = {}) {
  let cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  if (cleanEndpoint.startsWith("/api/")) {
    cleanEndpoint = cleanEndpoint.slice(4); // strip leading /api
  }
  const url = endpoint.startsWith("http") ? endpoint : `/api${cleanEndpoint}`;
  const defaultHeaders: Record<string, string> = {};
  if (!(options.body instanceof FormData)) {
      defaultHeaders["Content-Type"] = "application/json";
  }
  return fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });
}
