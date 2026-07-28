"use client";

import React from "react";

interface LoginModalProps {
  onClose: () => void;
}

export default function LoginModal({ onClose }: LoginModalProps) {
  const googleEnabled = true;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="modal-close" aria-label="Close">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="1" y1="1" x2="11" y2="11" />
            <line x1="11" y1="1" x2="1" y2="11" />
          </svg>
        </button>
        <div className="flex items-center gap-3 mb-7">
          <div className="w-7 h-7 flex items-center justify-center rounded-sm" style={{ background: "var(--txt)" }}>
            <div className="w-3.5 h-3.5 rotate-45" style={{ background: "var(--bg)" }}></div>
          </div>
          <span className="font-black text-sm tracking-widest uppercase" style={{ color: "var(--txt)" }}>DataForge</span>
        </div>
        <h2 className="text-xl font-black tracking-tight mb-1" style={{ color: "var(--txt)" }}>Sign in to continue</h2>
        <p className="text-sm mb-7" style={{ color: "var(--txt-m)" }}>Create an account or sign in to upload your dataset and start analysing.</p>
        {googleEnabled ? (
          <div className="flex flex-col gap-2 w-full">
            <a href="http://localhost:5000/login/google" className="google-btn">
              <svg width="18" height="18" viewBox="0 0 48 48">
                <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z" />
                <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z" />
                <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z" />
                <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z" />
              </svg>
              Continue with Google
            </a>
            <a href="http://localhost:5000/login/mock" className="google-btn" style={{ background: "rgba(255,255,255,0.05)", color: "#fff", border: "1px solid rgba(255,255,255,0.1)", marginTop: "0.25rem" }}>
              👤 Developer Sandbox Login
            </a>
          </div>
        ) : (
          <div className="p-4 rounded-xl" style={{ background: "rgba(245,158,11,.08)", border: "1px solid rgba(245,158,11,.2)" }}>
            <p className="text-xs font-bold text-amber-400 mb-1">⚠ Google OAuth not configured</p>
            <p className="text-xs" style={{ color: "var(--txt-m)" }}>Add Google credentials to your env and restart.</p>
          </div>
        )}
        <p className="text-center text-[10px] mt-5" style={{ color: "var(--txt-m)" }}>
          Your data is processed locally and never stored externally.
        </p>
      </div>
    </div>
  );
}
