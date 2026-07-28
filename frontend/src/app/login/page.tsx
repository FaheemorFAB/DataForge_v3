"use client";

import React, { useEffect } from "react";
import styles from "./login.module.css";
import Link from "next/link";

export default function LoginPage() {
  useEffect(() => {
    // Optionally set dark theme as default on mount
    document.documentElement.setAttribute("data-theme", "dark");
  }, []);

  return (
    <div className={styles.container}>
      <div className={styles.noise}></div>
      <div className={styles.mesh}></div>

      <div className={styles.card}>
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div
            className="w-8 h-8 flex items-center justify-center rounded-sm"
            style={{ background: "#fff" }}
          >
            <div
              className="w-4 h-4 rotate-45"
              style={{ background: "#050505" }}
            ></div>
          </div>
          <span className="font-black text-sm tracking-widest uppercase text-white">
            DataForge
          </span>
        </div>

        <h1 className="text-2xl font-black tracking-tight mb-1 text-white">Sign in</h1>
        <p className="text-sm mb-8" style={{ color: "var(--txt-m)" }}>
          to continue to your analytics dashboard
        </p>

        <a href="/api/auth/login/google" className={styles.googleBtn}>
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
        </a>

        <a href="http://localhost:5000/login/mock" className={styles.googleBtn} style={{ background: "rgba(255,255,255,0.05)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", marginTop: "0.75rem" }}>
          👤 Developer Sandbox Login
        </a>


        <p
          className="text-center text-[10px] mt-6"
          style={{ color: "var(--txt-m)" }}
        >
          By signing in you agree to our terms. Your data is processed locally
          and never stored externally.
        </p>
      </div>
    </div>
  );
}
