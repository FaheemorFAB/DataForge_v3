function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^|; )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}

export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;

  // 1. Check access_token in document.cookie
  const cookieToken = getCookie("access_token");
  if (cookieToken) return cookieToken;

  // 2. Check localStorage explicit keys
  try {
    const localToken = localStorage.getItem("access_token") || localStorage.getItem("df_access_token");
    if (localToken) return localToken;

    // 3. Check Supabase session keys (e.g. sb-<project>-auth-token)
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith("sb-") || key.includes("supabase")) && key.endsWith("-auth-token")) {
        const item = JSON.parse(localStorage.getItem(key) || "{}");
        if (item?.access_token) return item.access_token;
        if (item?.currentSession?.access_token) return item.currentSession.access_token;
      }
    }
  } catch {}

  return null;
}

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

  const token = getAuthToken();
  const existingHeaders = options.headers as Record<string, string> | undefined;
  if (token && !existingHeaders?.["Authorization"] && !existingHeaders?.["authorization"]) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  return fetch(url, {
    credentials: options.credentials ?? "include",
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });
}
