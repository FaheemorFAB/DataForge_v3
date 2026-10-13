import { useState, useEffect } from "react";
import { apiFetch } from "./api";
import { supabase } from "./supabase";

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
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Initial cached user hydration
    const cached = getCachedUser();
    if (cached) {
      setUser(cached);
      setLoading(false);
    }

    // 2. Check Supabase session first
    let mounted = true;
    async function initAuth() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.user && mounted) {
          const supaUser = {
            id: session.user.id,
            email: session.user.email,
            name: session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email?.split("@")[0] || "User",
            avatar: session.user.user_metadata?.avatar_url || "https://api.dicebear.com/7.x/pixel-art/svg",
            provider: "supabase",
          };
          setUser(supaUser);
          setCachedUser(supaUser);
          setLoading(false);
          return;
        }
      } catch (err) {
        // Supabase client may not have credentials configured yet
      }

      // 3. Fallback to DataForge backend /v1/auth/me
      try {
        const res = await apiFetch("/v1/auth/me");
        if (res.ok && mounted) {
          const data = await res.json();
          setUser(data);
          setCachedUser(data);
        } else if (mounted) {
          if (!cached) setUser(null);
        }
      } catch (e) {
        // Keep cached user on network error
      } finally {
        if (mounted) setLoading(false);
      }
    }

    initAuth();

    // 4. Supabase auth state change listener
    const { data: authListener } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session?.user) {
        const supaUser = {
          id: session.user.id,
          email: session.user.email,
          name: session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email?.split("@")[0] || "User",
          avatar: session.user.user_metadata?.avatar_url || "https://api.dicebear.com/7.x/pixel-art/svg",
          provider: "supabase",
        };
        setUser(supaUser);
        setCachedUser(supaUser);
      } else {
        // check backend before clearing
      }
    });

    return () => {
      mounted = false;
      authListener.subscription.unsubscribe();
    };
  }, []);

  const loginWithSupabase = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    if (data.user) {
      const supaUser = {
        id: data.user.id,
        email: data.user.email,
        name: data.user.user_metadata?.full_name || data.user.email?.split("@")[0] || "User",
        avatar: data.user.user_metadata?.avatar_url || "https://api.dicebear.com/7.x/pixel-art/svg",
        provider: "supabase",
      };
      setUser(supaUser);
      setCachedUser(supaUser);
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
    try {
      await supabase.auth.signOut();
    } catch {}
    try {
      await apiFetch("/v1/auth/logout", { method: "POST" });
    } catch {}
    setUser(null);
    setCachedUser(null);
    window.location.href = "/";
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
