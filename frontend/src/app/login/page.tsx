"use client";

import React, { useState, useEffect } from "react";
import styles from "./login.module.css";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Mail, Lock, Sparkles, ArrowRight, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { loginWithSupabase, signupWithSupabase, loginWithOAuth } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "dark");
  }, []);

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setErrorMsg("Please enter both email and password.");
      return;
    }
    setLoading(true);
    setErrorMsg("");
    setStatusMsg("");

    try {
      if (isSignUp) {
        await signupWithSupabase(email, password);
        setStatusMsg("Account created! Check your email to confirm or sign in directly.");
      } else {
        await loginWithSupabase(email, password);
        router.push("/workspace");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Authentication failed. Check your Supabase credentials in .env");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth = async (provider: "google" | "github") => {
    setLoading(true);
    setErrorMsg("");
    try {
      await loginWithOAuth(provider);
    } catch (err: any) {
      setErrorMsg(err.message || "OAuth redirection failed");
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.noise}></div>
      <div className={styles.mesh}></div>

      <div className={styles.card}>
        {/* Logo */}
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-8 h-8 flex items-center justify-center rounded-sm"
            style={{ background: "#fff" }}
          >
            <div className="w-4 h-4 rotate-45" style={{ background: "#050505" }}></div>
          </div>
          <span className="font-black text-sm tracking-widest uppercase text-white">
            DataForge
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            Supabase Auth
          </span>
        </div>

        <h1 className="text-2xl font-black tracking-tight mb-1 text-white">
          {isSignUp ? "Create an account" : "Welcome back"}
        </h1>
        <p className="text-xs mb-6" style={{ color: "var(--txt-m)" }}>
          Powered by Supabase Auth with encrypted sessions
        </p>

        {/* OAuth Buttons */}
        <div className="space-y-2 mb-4">
          <button
            type="button"
            onClick={() => handleOAuth("google")}
            disabled={loading}
            className={styles.googleBtn}
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
            Continue with Google
          </button>
        </div>

        <div className="flex items-center gap-3 my-4">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-[11px] font-mono text-zinc-500 uppercase">or with email</span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        {/* Email & Password Form */}
        <form onSubmit={handleEmailAuth} className="space-y-3">
          <div>
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 bg-white/5">
              <Mail size={14} className="text-zinc-400" />
              <input
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="bg-transparent text-xs text-white focus:outline-none w-full"
                required
              />
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 bg-white/5">
              <Lock size={14} className="text-zinc-400" />
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="bg-transparent text-xs text-white focus:outline-none w-full"
                required
              />
            </div>
          </div>

          {errorMsg && (
            <p className="text-[11px] font-mono text-rose-400 bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20">
              {errorMsg}
            </p>
          )}

          {statusMsg && (
            <p className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 p-2.5 rounded-lg border border-emerald-500/20">
              {statusMsg}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl text-xs font-bold bg-[var(--accent)] text-white hover:opacity-95 transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-lg shadow-[var(--accent)]/20"
          >
            <span>{loading ? "Authenticating..." : isSignUp ? "Sign Up with Supabase" : "Sign In with Supabase"}</span>
            <ArrowRight size={13} />
          </button>
        </form>

        {/* Switch Sign In / Sign Up */}
        <div className="mt-4 text-center">
          <button
            type="button"
            onClick={() => {
              setIsSignUp(!isSignUp);
              setErrorMsg("");
              setStatusMsg("");
            }}
            className="text-[11px] text-zinc-400 hover:text-white transition-colors cursor-pointer"
          >
            {isSignUp ? "Already have an account? Sign in" : "Need an account? Sign up with Supabase"}
          </button>
        </div>

        {/* Direct Workspace Bypass for Dev/Testing */}
        <div className="mt-6 pt-4 border-t border-white/10 text-center">
          <Link
            href="/workspace"
            className="text-[11px] font-mono text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Continue as Guest / Enter Workspace Directly →
          </Link>
        </div>
      </div>
    </div>
  );
}
