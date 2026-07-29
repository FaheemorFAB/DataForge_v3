import { useState, useEffect } from "react";
import { apiFetch } from "./api";

const CACHE_KEY = "df_user_cache";

function getCachedUser(): any | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function setCachedUser(user: any | null) {
  if (typeof window === "undefined") return;
  try {
    if (user) {
      localStorage.setItem(CACHE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(CACHE_KEY);
    }
  } catch {}
}

export function useAuth() {
  // Always start with null so the server and client render the same initial HTML.
  // The cached user is loaded in useEffect (client-only) to avoid hydration mismatches.
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Hydrate from localStorage cache immediately (client-only) so the UI
    // shows the correct state before the API call resolves.
    const cached = getCachedUser();
    if (cached) {
      setUser(cached);
      setLoading(false);
    }

    const checkAuth = async () => {
      try {
        const res = await apiFetch("/v1/auth/me");
        if (res.ok) {
          const data = await res.json();
          setUser(data);
          setCachedUser(data);
        } else {
          setUser(null);
          setCachedUser(null);
        }
      } catch (e) {
        // Network error — keep cached user to avoid flash,
        // but don't clear it (might just be backend restarting)
      } finally {
        setLoading(false);
      }
    };
    checkAuth();
  }, []);

  const logout = async () => {
    try {
      await apiFetch("/v1/auth/logout", { method: "POST" });
    } catch (e) {}
    setUser(null);
    setCachedUser(null);
    window.location.href = "/";
  };

  return { user, loading, logout };
}
