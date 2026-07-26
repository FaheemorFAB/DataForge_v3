import { useState, useEffect } from "react";
import { apiFetch } from "./api";

export function useAuth() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real implementation this would check cookies/session with the backend
    const checkAuth = async () => {
      try {
        const res = await apiFetch("/v1/auth/me");
        if (res.ok) {
          const data = await res.json();
          setUser(data);
        } else {
          setUser(null);
        }
      } catch (e) {
        setUser(null);
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
    window.location.href = "/";
  };

  return { user, loading, logout };
}
