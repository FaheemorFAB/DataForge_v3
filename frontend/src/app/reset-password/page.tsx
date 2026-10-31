"use client";

import React, { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, AlertCircle, ShieldCheck } from "lucide-react";

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
    document.documentElement.setAttribute("data-theme", "dark");

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
          // If network failed but token exists, still allow submission attempt
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
    <div className="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden bg-[#090d16]">
      {/* Background Ambience */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03] z-[9999] bg-[radial-gradient(#fff_1px,transparent_1px)] [background-size:16px_16px]" />
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.15)_0%,transparent_50%),radial-gradient(circle_at_80%_80%,rgba(30,10,60,0.4)_0%,transparent_50%)]" />

      {/* Main Card */}
      <div className="w-full max-w-[420px] bg-[#0f172a]/90 border border-slate-800 rounded-3xl p-8 backdrop-blur-xl shadow-2xl relative z-10">
        {/* Brand Header */}
        <div className="flex items-center justify-between mb-6">
          <Link href="/" className="flex items-center gap-2.5 text-decoration-none">
            <div
              className="w-8 h-8 flex items-center justify-center rounded-sm"
              style={{ background: "#fff" }}
            >
              <div className="w-4 h-4 rotate-45" style={{ background: "#050505" }}></div>
            </div>
            <span className="font-black text-sm tracking-widest uppercase text-white">
              DataForge
            </span>
          </Link>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            Password Reset
          </span>
        </div>

        {/* State 1: Verifying Token */}
        {verifying && (
          <div className="py-8 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-zinc-400 font-mono">Verifying secure reset token...</p>
          </div>
        )}

        {/* State 2: Invalid / Expired Token */}
        {!verifying && !tokenValid && (
          <div className="space-y-5">
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 space-y-2">
              <div className="flex items-center gap-2 font-bold text-sm">
                <AlertCircle size={16} className="text-rose-400 shrink-0" />
                <span>Link Invalid or Expired</span>
              </div>
              <p className="text-xs leading-relaxed text-zinc-300">
                {tokenError || "This password reset link is invalid or has expired."}
              </p>
            </div>

            <div className="pt-2 flex flex-col gap-2">
              <Link
                href="/login?mode=forgot"
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white transition-all flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/20 text-decoration-none"
              >
                <span>Request a New Reset Link</span>
                <ArrowRight size={13} />
              </Link>
              <Link
                href="/login"
                className="w-full py-2.5 rounded-xl text-xs font-semibold text-zinc-400 hover:text-white transition-colors flex items-center justify-center gap-1.5 text-decoration-none"
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
              <h1 className="text-2xl font-black tracking-tight mb-1 text-white">
                Set New Password
              </h1>
              <p className="text-xs text-zinc-400">
                {maskedEmail
                  ? `Enter a new password for account (${maskedEmail})`
                  : "Enter a strong, secure new password for your account"}
              </p>
            </div>

            {success ? (
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 space-y-2 text-center py-6">
                <CheckCircle2 size={32} className="text-emerald-400 mx-auto" />
                <h3 className="font-bold text-sm text-white">Password Updated!</h3>
                <p className="text-xs text-zinc-400">
                  Your credentials have been securely updated. Redirecting you to your workspace...
                </p>
              </div>
            ) : (
              <form noValidate onSubmit={handleSubmit} className="space-y-3.5">
                <div>
                  <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                    New Password
                  </label>
                  <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 bg-white/5 focus-within:border-indigo-500/50 transition-colors">
                    <Lock size={14} className="text-zinc-400 shrink-0" />
                    <input
                      type="password"
                      placeholder="At least 8 characters"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="bg-transparent text-xs text-white focus:outline-none w-full"
                      autoComplete="new-password"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-zinc-400 mb-1">
                    Confirm New Password
                  </label>
                  <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 bg-white/5 focus-within:border-indigo-500/50 transition-colors">
                    <Lock size={14} className="text-zinc-400 shrink-0" />
                    <input
                      type="password"
                      placeholder="Repeat your new password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="bg-transparent text-xs text-white focus:outline-none w-full"
                      autoComplete="new-password"
                      required
                    />
                  </div>
                </div>

                {formError && (
                  <div className="flex items-start gap-2 text-[11px] font-medium text-rose-400 bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20">
                    <AlertCircle size={14} className="shrink-0 mt-0.5" />
                    <span>{formError}</span>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 mt-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-lg shadow-indigo-600/20 disabled:opacity-50"
                >
                  <span>{loading ? "Updating Password..." : "Update Password"}</span>
                  <ArrowRight size={13} />
                </button>

                <div className="pt-2 text-center">
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white transition-colors text-decoration-none"
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
        <div className="min-h-screen flex items-center justify-center bg-[#090d16] text-white text-xs font-mono">
          Loading DataForge Security...
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}

