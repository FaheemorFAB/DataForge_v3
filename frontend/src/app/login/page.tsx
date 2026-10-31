"use client";

import React, { useState, useEffect, Suspense } from "react";
import styles from "./login.module.css";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Logo from "../components/Logo";
import ThemeSwitcher from "../components/ThemeSwitcher";
import { Mail, Lock, User as UserIcon, ArrowRight, ArrowLeft, CheckCircle2, AlertCircle } from "lucide-react";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { loginWithSupabase, signupWithSupabase, resetPasswordForEmail } = useAuth();

  const [mode, setMode] = useState<"signin" | "signup" | "forgot">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [resetSent, setResetSent] = useState(false);

  useEffect(() => {
    // Respect the user's saved theme from localStorage instead of hardcoding dark mode
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

    const m = searchParams.get("mode");
    if (m === "signup" || m === "forgot") {
      setMode(m);
    }
  }, [searchParams]);

  const switchMode = (newMode: "signin" | "signup" | "forgot") => {
    setMode(newMode);
    setErrorMsg("");
    setStatusMsg("");
    setResetSent(false);
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setStatusMsg("");

    if (!email) {
      setErrorMsg("Please enter your email address.");
      return;
    }

    if (mode === "forgot") {
      setLoading(true);
      try {
        await resetPasswordForEmail(email);
        setResetSent(true);
        setStatusMsg("Reset instructions have been dispatched to your inbox. Please check your email to continue.");
      } catch (err: any) {
        setErrorMsg(err.message || "Unable to send reset email. Please try again.");
      } finally {
        setLoading(false);
      }
      return;
    }

    if (!password) {
      setErrorMsg("Please enter your password.");
      return;
    }

    if (mode === "signup" && password.length < 8) {
      setErrorMsg("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);
    try {
      if (mode === "signup") {
        const res = await signupWithSupabase(email, password, name.trim() || undefined);
        if (res.session?.access_token) {
          router.push("/workspace");
        } else {
          setStatusMsg("Account created! Check your email to confirm or sign in directly.");
        }
      } else {
        await loginWithSupabase(email, password);
        router.push("/workspace");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Authentication failed. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.noise}></div>
      <div className={styles.mesh}></div>

      {/* Floating Theme Switcher at Top Right of Screen */}
      <div className="fixed top-5 right-5 z-50">
        <ThemeSwitcher />
      </div>

      <div className={styles.card}>
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

        {/* Title & Description */}
        <div className="mb-5">
          <h1 className="text-2xl font-black tracking-tight mb-1" style={{ color: "var(--txt)" }}>
            {mode === "signup"
              ? "Create your account"
              : mode === "forgot"
                ? "Reset your password"
                : "Welcome back"}
          </h1>
          <p className="text-xs" style={{ color: "var(--txt-m)" }}>
            {mode === "signup"
              ? "Start analyzing, transforming, and collaborating with DataForge"
              : mode === "forgot"
                ? "Enter your account email to receive a secure reset link"
                : "Sign in to access your personal and team workspaces"}
          </p>
        </div>

        {/* Continue with Google button */}
        {mode !== "forgot" && (
          <>
            <div className="space-y-2 mb-4">
              <a
                href="/api/auth/login/google"
                className={styles.googleBtn}
                style={{ textDecoration: "none" }}
              >
                <svg width="18" height="18" viewBox="0 0 48 48">
                  <path
                    fill="#EA4335"
                    d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
                  />
                  <path
                    fill="#4285F4"
                    d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
                  />
                  <path
                    fill="#34A853"
                    d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
                  />
                </svg>
                <span>Continue with Google</span>
              </a>
            </div>

            <div className="flex items-center gap-3 my-4">
              <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
              <span className="text-[10px] font-mono tracking-widest uppercase" style={{ color: "var(--txt-f)" }}>
                or with email
              </span>
              <div className="flex-1 h-px" style={{ background: "var(--border)" }} />
            </div>
          </>
        )}

        {/* Auth Form */}
        <form noValidate onSubmit={handleEmailAuth} className="space-y-3">
          {/* Full Name (Sign Up only) */}
          {mode === "signup" && (
            <div>
              <label className="block text-[11px] font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                Full Name
              </label>
              <div
                className="flex items-center gap-2 px-3 py-2.5 rounded-xl border transition-colors"
                style={{
                  background: "var(--inp-bg)",
                  borderColor: "var(--border)",
                }}
              >
                <UserIcon size={14} className="shrink-0" style={{ color: "var(--txt-f)" }} />
                <input
                  type="text"
                  placeholder="Jane Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-transparent text-xs focus:outline-none w-full"
                  style={{ color: "var(--txt)" }}
                  autoComplete="name"
                />
              </div>
            </div>
          )}

          {/* Email Address */}
          <div>
            <label className="block text-[11px] font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
              Work Email
            </label>
            <div
              className="flex items-center gap-2 px-3 py-2.5 rounded-xl border transition-colors"
              style={{
                background: "var(--inp-bg)",
                borderColor: "var(--border)",
              }}
            >
              <Mail size={14} className="shrink-0" style={{ color: "var(--txt-f)" }} />
              <input
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-transparent text-xs focus:outline-none w-full"
                style={{ color: "var(--txt)" }}
                autoComplete="email"
                required
              />
            </div>
          </div>

          {/* Password (Sign In & Sign Up) */}
          {mode !== "forgot" && (
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-[11px] font-semibold" style={{ color: "var(--txt-m)" }}>
                  Password
                </label>
                {mode === "signin" && (
                  <button
                    type="button"
                    onClick={() => switchMode("forgot")}
                    className="text-[11px] font-medium transition-colors cursor-pointer"
                    style={{ color: "var(--accent)" }}
                  >
                    Forgot password?
                  </button>
                )}
              </div>
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
                  placeholder={mode === "signup" ? "At least 8 characters" : "••••••••"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-transparent text-xs focus:outline-none w-full"
                  style={{ color: "var(--txt)" }}
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  required
                />
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMsg && (
            <div className="flex items-start gap-2 text-[11px] font-medium text-rose-500 bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Status Message */}
          {statusMsg && (
            <div className="flex items-start gap-2 text-[11px] font-medium text-emerald-500 bg-emerald-500/10 p-2.5 rounded-lg border border-emerald-500/20">
              <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
              <span>{statusMsg}</span>
            </div>
          )}

          {/* Submit Button */}
          {(!resetSent || mode !== "forgot") && (
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 mt-2 rounded-xl text-xs font-bold text-white transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-lg disabled:opacity-50 hover:opacity-95"
              style={{
                background: "var(--accent)",
                boxShadow: "0 4px 14px var(--glow)",
              }}
            >
              <span>
                {loading
                  ? "Processing..."
                  : mode === "signup"
                    ? "Create Account"
                    : mode === "forgot"
                      ? "Send Reset Link"
                      : "Sign In"}
              </span>
              <ArrowRight size={13} />
            </button>
          )}
        </form>

        {/* Footer / Switch View */}
        <div
          className="mt-5 pt-4 border-t text-center"
          style={{ borderColor: "var(--border)" }}
        >
          {mode === "forgot" ? (
            <button
              type="button"
              onClick={() => switchMode("signin")}
              className="inline-flex items-center gap-1.5 text-xs transition-colors cursor-pointer"
              style={{ color: "var(--txt-m)" }}
            >
              <ArrowLeft size={13} />
              <span>Back to Sign In</span>
            </button>
          ) : mode === "signup" ? (
            <p className="text-xs" style={{ color: "var(--txt-m)" }}>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => switchMode("signin")}
                className="font-semibold cursor-pointer underline-offset-2 hover:underline"
                style={{ color: "var(--accent)" }}
              >
                Sign In
              </button>
            </p>
          ) : (
            <p className="text-xs" style={{ color: "var(--txt-m)" }}>
              Don't have an account?{" "}
              <button
                type="button"
                onClick={() => switchMode("signup")}
                className="font-semibold cursor-pointer underline-offset-2 hover:underline"
                style={{ color: "var(--accent)" }}
              >
                Create one now
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.container}>
          <div className="text-xs font-mono" style={{ color: "var(--txt-m)" }}>
            Loading DataForge Auth...
          </div>
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
