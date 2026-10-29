import { useState, useEffect } from "react";
import { apiFetch, getAuthToken } from "./api";
import { supabase } from "./supabase";

const CACHE_KEY = "df_user_cache";

export function clearAuthSession() {
  if (typeof window === "undefined") return;

  // 1. Wipe client-accessible cookies across common path/domain permutations
  const cookieNames = ["access_token", "token", "df_access_token", "df_session"];
  const paths = ["/", "/api", "/v1", "/workspace"];
  const host = window.location.hostname;
  const domainPermutations = ["", host, `.${host}`];

  for (const name of cookieNames) {
    for (const p of paths) {
      for (const d of domainPermutations) {
        const domAttr = d ? `; domain=${d}` : "";
        document.cookie = `${name}=; path=${p}${domAttr}; expires=Thu, 01 Jan 1970 00:00:00 GMT; max-age=0; SameSite=Lax`;
        document.cookie = `${name}=; path=${p}${domAttr}; expires=Thu, 01 Jan 1970 00:00:00 GMT; max-age=0; SameSite=None; Secure`;
      }
    }
  }

  // 2. Wipe explicit tokens and Supabase session keys from localStorage
  try {
    localStorage.removeItem("access_token");
    localStorage.removeItem("df_access_token");
    localStorage.removeItem(CACHE_KEY);

    const keysToRemove: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (
        key &&
        (key.startsWith("sb-") ||
          key.includes("supabase") ||
          key.endsWith("-auth-token") ||
          key.toLowerCase().includes("token") ||
          key.toLowerCase().includes("auth"))
      ) {
        keysToRemove.push(key);
      }
    }
    for (const k of keysToRemove) {
      localStorage.removeItem(k);
    }
  } catch {}

  // 3. Clear sessionStorage
  try {
    sessionStorage.clear();
  } catch {}
}

function getCachedUser(): any | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || !parsed.email) return null;
    if (
      parsed?.email === "admin@dataforge.app" ||
      parsed?.email === "dev@example.com" ||
      parsed?.email === "analyst@dataforge.app" ||
      parsed?.email === "user_1@dataforge.app"
    ) {
      localStorage.removeItem(CACHE_KEY);
      return null;
    }
    const localAvatar = localStorage.getItem("df_user_avatar");
    if (localAvatar) {
      parsed.avatar = localAvatar;
    } else if (parsed?.avatar && parsed.avatar.includes("dicebear")) {
      parsed.avatar = "/avatars/avatar-1.svg";
      localStorage.setItem(CACHE_KEY, JSON.stringify(parsed));
    }
    return parsed;
  } catch {
    return null;
  }
}

function setCachedUser(user: any | null) {
  if (typeof window === "undefined") return;
  try {
    const localAvatar = localStorage.getItem("df_user_avatar");
    if (user) {
      if (localAvatar) {
        user.avatar = localAvatar;
      }
      localStorage.setItem(CACHE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(CACHE_KEY);
    }
  } catch {}
}

export function useAuth() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 0. Extract token from URL if returning from OAuth
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const urlToken = urlParams.get("token");
      if (urlToken) {
        document.cookie = `access_token=${urlToken}; path=/; max-age=604800; SameSite=Lax`;
        try {
          localStorage.setItem("access_token", urlToken);
        } catch {}
        urlParams.delete("token");
        const newSearch = urlParams.toString() ? `?${urlParams.toString()}` : "";
        window.history.replaceState({}, "", `${window.location.pathname}${newSearch}`);
      }
    }

    // 1. Initial cached user hydration (only if token exists or was remembered)
    const token = getAuthToken();
    const cached = getCachedUser();
    if (token && cached) {
      setUser(cached);
      setLoading(false);
    } else if (!token) {
      setCachedUser(null);
    }

    // 2. Global event listener so all mounted components stay in sync
    const handleAuthEvent = (e: any) => {
      setUser(e.detail ?? null);
      setLoading(false);
    };
    if (typeof window !== "undefined") {
      window.addEventListener("dataforge:auth-state", handleAuthEvent);
    }

    // 3. Check Supabase session first
    let mounted = true;
    async function initAuth() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.user && mounted) {
          if (session.access_token) {
            document.cookie = `access_token=${session.access_token}; path=/; max-age=604800; SameSite=Lax`;
            localStorage.setItem("access_token", session.access_token);
          }
          const localAvatar = typeof window !== "undefined" ? localStorage.getItem("df_user_avatar") : null;
          const supaUser = {
            id: session.user.id,
            email: session.user.email,
            name: session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email?.split("@")[0] || "User",
            avatar: localAvatar || session.user.user_metadata?.avatar_url || "/avatars/avatar-1.svg",
            provider: "supabase",
            role: "Admin",
          };
          setUser(supaUser);
          setCachedUser(supaUser);
          setLoading(false);
          return;
        }
      } catch (err) {
        // Supabase client may not be configured
      }

      // 4. Fallback to DataForge backend /v1/auth/me
      try {
        const res = await apiFetch("/v1/auth/me");
        if (res.ok && mounted) {
          const data = await res.json();
          const localAvatar = typeof window !== "undefined" ? localStorage.getItem("df_user_avatar") : null;
          if (localAvatar) {
            data.avatar = localAvatar;
          } else if (data?.avatar && data.avatar.includes("dicebear")) {
            data.avatar = "/avatars/avatar-1.svg";
          }
          setUser(data);
          setCachedUser(data);
        } else if (mounted) {
          setUser(null);
          setCachedUser(null);
        }
      } catch (e) {
        if (mounted) {
          setUser(null);
          setCachedUser(null);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    initAuth();

    // 5. Supabase auth state change listener
    const { data: authListener } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session?.user) {
        if (session.access_token) {
          document.cookie = `access_token=${session.access_token}; path=/; max-age=604800; SameSite=Lax`;
          localStorage.setItem("access_token", session.access_token);
        }
        const supaUser = {
          id: session.user.id,
          email: session.user.email,
          name: session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email?.split("@")[0] || "User",
          avatar: session.user.user_metadata?.avatar_url || "/avatars/avatar-1.svg",
          provider: "supabase",
        };
        setUser(supaUser);
        setCachedUser(supaUser);
      }
    });

    return () => {
      mounted = false;
      authListener.subscription.unsubscribe();
      if (typeof window !== "undefined") {
        window.removeEventListener("dataforge:auth-state", handleAuthEvent);
      }
    };
  }, []);

  const loginWithSupabase = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    if (data.user) {
      if (data.session?.access_token) {
        document.cookie = `access_token=${data.session.access_token}; path=/; max-age=604800; SameSite=Lax`;
        localStorage.setItem("access_token", data.session.access_token);
      }
      const supaUser = {
        id: data.user.id,
        email: data.user.email,
        name: data.user.user_metadata?.full_name || data.user.email?.split("@")[0] || "User",
        avatar: data.user.user_metadata?.avatar_url || "/avatars/avatar-1.svg",
        provider: "supabase",
      };
      setUser(supaUser);
      setCachedUser(supaUser);
      if (typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("dataforge:auth-state", { detail: supaUser }));
      }
    }
    return data;
  };

  const signupWithSupabase = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
    return data;
  };

  const loginWithOAuth = async (provider: "google" | "github") => {
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: typeof window !== "undefined" ? `${window.location.origin}/workspace` : undefined,
      },
    });
    if (error) throw error;
    return data;
  };

  const logout = async () => {
    // 1. Immediately wipe client credentials and caches
    clearAuthSession();
    setUser(null);
    setCachedUser(null);

    // 2. Broadcast auth state change immediately to all mounted components (e.g. Header)
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("dataforge:auth-state", { detail: null }));
    }

    // 3. Clear Supabase local session
    try {
      await supabase.auth.signOut({ scope: "local" });
    } catch {}

    // 4. Request backend cookie clearance
    try {
      await apiFetch("/v1/auth/logout", { method: "POST" });
    } catch {}
    try {
      await fetch("/api/logout", { method: "POST", credentials: "include" });
    } catch {}

    // 5. Navigate to landing page or reload if already on landing
    if (typeof window !== "undefined") {
      if (window.location.pathname === "/" && !window.location.search && !window.location.hash) {
        window.location.reload();
      } else {
        window.location.href = "/";
      }
    }
  };

  return {
    user,
    loading,
    logout,
    loginWithSupabase,
    signupWithSupabase,
    loginWithOAuth,
  };
}
