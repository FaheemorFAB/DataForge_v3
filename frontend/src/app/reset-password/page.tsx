"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Logo from "../components/Logo";
import ThemeSwitcher from "../components/ThemeSwitcher";
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, AlertCircle } from "lucide-react";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [token, setToken] = useState<string>("");
  const [supabaseRecovery, setSupabaseRecovery] = useState<boolean>(false);
  const [verifying, setVerifying] = useState<boolean>(true);
  const [tokenValid, setTokenValid] = useState<boolean>(false);
  const [maskedEmail, setMaskedEmail] = useState<string>("");
  const [tokenError, setTokenError] = useState<string>("");

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    // Respect the user's saved theme from localStorage
    if (typeof window !== "undefined") {
      const savedTheme = localStorage.getItem("analyst-theme") || "dark";
      document.documentElement.setAttribute("data-theme", savedTheme);
      const darkThemes = ["dark", "dracula", "slate", "emerald", "nord", "luxury"];
      if (darkThemes.includes(savedTheme)) {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    }

    const queryToken = searchParams.get("token");
    let hasSupabaseRecovery = false;

    if (typeof window !== "undefined") {
      const hash = window.location.hash;
      if (hash && (hash.includes("type=recovery") || hash.includes("access_token="))) {
        hasSupabaseRecovery = true;
        setSupabaseRecovery(true);
      }
    }

    if (queryToken) {
      setToken(queryToken);
      // Verify token with backend
      fetch(`/api/auth/password/verify-token?token=${encodeURIComponent(queryToken)}`)
        .then((res) => res.json())
        .then((data) => {
          if (data.valid) {
            setTokenValid(true);
            if (data.email) setMaskedEmail(data.email);
          } else {
            setTokenValid(false);
            setTokenError(data.reason || "This password reset link is invalid or has expired.");
          }
        })
        .catch(() => {
          setTokenValid(true);
        })
        .finally(() => {
          setVerifying(false);
        });
    } else if (hasSupabaseRecovery) {
      setTokenValid(true);
      setVerifying(false);
    } else {
      setVerifying(false);
      setTokenValid(false);
      setTokenError("No reset token found in link. Please request a new password reset link.");
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!newPassword || !confirmPassword) {
      setFormError("Please fill in both password fields.");
      return;
    }

    if (newPassword.length < 8) {
      setFormError("Password must be at least 8 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }

    setLoading(true);

    try {
      let backendSuccess = false;

      // 1. Submit to backend if token is available
      if (token) {
        const res = await fetch("/api/auth/password/reset", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, new_password: newPassword }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || data.message || "Failed to update password.");
        }
        if (data.token) {
          document.cookie = `access_token=${data.token}; path=/; max-age=604800; SameSite=Lax`;
          try {
            localStorage.setItem("access_token", data.token);
          } catch {}
        }
        backendSuccess = true;
      }

      // 2. Also update Supabase user password if recovery session is active
      try {
        const { error: supaErr } = await supabase.auth.updateUser({ password: newPassword });
        if (supaErr && !backendSuccess) {
          throw supaErr;
        }
      } catch (err: any) {
        if (!backendSuccess) throw err;
      }

      setSuccess(true);
      setTimeout(() => {
        router.push("/workspace");
      }, 1500);
    } catch (err: any) {
      setFormError(err.message || "Could not update password. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden transition-colors duration-300"
      style={{ background: "var(--bg)", color: "var(--txt)" }}
    >
      {/* Background Ambience */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] z-[9999] bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px]" />
      <div
        className="fixed inset-0 -z-10"
        style={{
          background: "radial-gradient(circle at 20% 20%, var(--glow) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(99, 102, 241, 0.08) 0%, transparent 50%)",
        }}
      />

      {/* Floating Theme Switcher at Top Right */}
      <div className="fixed top-5 right-5 z-50">
        <ThemeSwitcher />
      </div>

      {/* Main Card */}
      <div
        className="w-full max-w-[420px] rounded-3xl p-8 backdrop-blur-xl shadow-2xl relative z-10 border transition-all duration-300"
        style={{
          background: "var(--card)",
          borderColor: "var(--border)",
          boxShadow: "0 20px 40px -15px rgba(0, 0, 0, 0.2)",
        }}
      >
        {/* Brand Header */}
        <div className="flex items-center justify-between mb-6">
          <Link href="/" className="flex items-center gap-2.5 no-underline group">
            <Logo size={28} showText={false} />
            <span
              className="font-black text-sm tracking-widest uppercase transition-colors"
              style={{ color: "var(--txt)" }}
            >
              DataForge
            </span>
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all no-underline cursor-pointer"
            style={{
              background: "var(--inp-bg)",
              borderColor: "var(--border)",
              color: "var(--txt-m)",
            }}
          >
            <ArrowLeft size={13} />
            <span>Back to Home</span>
          </Link>
        </div>

        {/* State 1: Verifying Token */}
        {verifying && (
          <div className="py-8 text-center space-y-3">
            <div
              className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto"
              style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
            />
            <p className="text-xs font-mono" style={{ color: "var(--txt-m)" }}>Verifying secure reset token...</p>
          </div>
        )}

        {/* State 2: Invalid / Expired Token */}
        {!verifying && !tokenValid && (
          <div className="space-y-5">
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-500 space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <AlertCircle size={16} className="text-rose-500 shrink-0" />
                <span>Link Invalid or Expired</span>
              </div>
              <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                {tokenError || "This password reset link is invalid or has expired."}
              </p>
            </div>

            <div className="pt-2 flex flex-col gap-2">
              <Link
                href="/login?mode=forgot"
                className="w-full py-2.5 rounded-xl text-xs font-bold text-white transition-all flex items-center justify-center gap-1.5 no-underline shadow-lg"
                style={{
                  background: "var(--accent)",
                  boxShadow: "0 4px 14px var(--glow)",
                }}
              >
                <span>Request a New Reset Link</span>
                <ArrowRight size={13} />
              </Link>
              <Link
                href="/login"
                className="w-full py-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 no-underline transition-colors"
                style={{ color: "var(--txt-m)" }}
              >
                <ArrowLeft size={13} />
                <span>Back to Sign In</span>
              </Link>
            </div>
          </div>
        )}

        {/* State 3: Valid Token - Form */}
        {!verifying && tokenValid && (
          <>
            <div className="mb-5">
              <h1 className="text-2xl font-black tracking-tight mb-1" style={{ color: "var(--txt)" }}>
                Set New Password
              </h1>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                {maskedEmail
                  ? `Enter a new password for account (${maskedEmail})`
                  : "Enter a strong, secure new password for your account"}
              </p>
            </div>

            {success ? (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 space-y-2 text-center py-6">
                <CheckCircle2 size={32} className="text-emerald-500 mx-auto" />
                <h3 className="font-bold text-sm" style={{ color: "var(--txt)" }}>Password Updated!</h3>
                <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                  Your credentials have been securely updated. Redirecting you to your workspace...
                </p>
              </div>
            ) : (
              <form noValidate onSubmit={handleSubmit} className="space-y-3.5">
                <div>
                  <label className="block text-[11px] font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    New Password
                  </label>
                  <div
                    className="flex items-center gap-2 px-3 py-2.5 rounded-xl border transition-colors"
                    style={{
                      background: "var(--inp-bg)",
                      borderColor: "var(--border)",
                    }}
                  >
                    <Lock size={14} className="shrink-0" style={{ color: "var(--txt-f)" }} />
                    <input
                      type="password"
                      placeholder="At least 8 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="bg-transparent text-xs focus:outline-none w-full"
                      style={{ color: "var(--txt)" }}
                      autoComplete="new-password"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Confirm New Password
                  </label>
                  <div
                    className="flex items-center gap-2 px-3 py-2.5 rounded-xl border transition-colors"
                    style={{
                      background: "var(--inp-bg)",
                      borderColor: "var(--border)",
                    }}
                  >
                    <Lock size={14} className="shrink-0" style={{ color: "var(--txt-f)" }} />
                    <input
                      type="password"
                      placeholder="Repeat your new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="bg-transparent text-xs focus:outline-none w-full"
                      style={{ color: "var(--txt)" }}
                      autoComplete="new-password"
                      required
                    />
                  </div>
                </div>

                {formError && (
                  <div className="flex items-start gap-2 text-[11px] font-medium text-rose-500 bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20">
                    <AlertCircle size={14} className="shrink-0 mt-0.5" />
                    <span>{formError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 mt-2 rounded-xl text-xs font-bold text-white transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-lg disabled:opacity-50 hover:opacity-95"
                  style={{
                    background: "var(--accent)",
                    boxShadow: "0 4px 14px var(--glow)",
                  }}
                >
                  <span>{loading ? "Updating Password..." : "Update Password"}</span>
                  <ArrowRight size={13} />
                </button>

                <div className="pt-2 text-center">
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-1.5 text-xs transition-colors no-underline"
                    style={{ color: "var(--txt-m)" }}
                  >
                    <ArrowLeft size={13} />
                    <span>Back to Sign In</span>
                  </Link>
                </div>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div
          className="min-h-screen flex items-center justify-center text-xs font-mono"
          style={{ background: "var(--bg)", color: "var(--txt-m)" }}
        >
          Loading DataForge Security...
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}
