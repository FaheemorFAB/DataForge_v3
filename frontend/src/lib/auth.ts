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
  const [user, setUser] = useState<any>(() => getCachedUser());
  const [loading, setLoading] = useState(() => !getCachedUser());

  useEffect(() => {
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
