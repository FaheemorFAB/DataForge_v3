"use client";

import React from "react";
import Link from "next/link";
import ThemeSwitcher from "../ThemeSwitcher";
import Logo from "../Logo";
import { useAuth } from "@/lib/auth";

interface HeaderProps {
  onLoginClick: () => void;
}

export default function Header({ onLoginClick }: HeaderProps) {
  const { user, loading: authLoading } = useAuth();
  const isLoggedIn = !!user;
  const [toast, setToast] = React.useState<string | null>(null);

  const handleDashboardClick = (e: React.MouseEvent) => {
    if (!localStorage.getItem('df_last_upload')) {
      e.preventDefault();
      setToast("Please upload a dataset first to access the dashboard!");
      setTimeout(() => setToast(null), 3500);
    }
  };

  return (
    <>
      <header className="px-5 md:px-8 py-4 flex justify-between items-center border-b sticky top-0 z-50 backdrop-blur-md" style={{ background: "var(--nav)", borderColor: "var(--border)" }}>
        <div className="flex items-center gap-3">
          <Link href="/">
            <Logo />
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/about" className="text-[11px] font-bold transition-colors hover:text-[var(--accent)]" style={{ color: "var(--txt-m)", textDecoration: "none" }}>
            About Us
          </Link>
          <ThemeSwitcher />
          {!authLoading && isLoggedIn ? (
            <Link href="/workspace" className="flex items-center gap-2 pl-2 pr-3 py-1 rounded-lg border transition-colors hover:border-[var(--accent)]" style={{ borderColor: "var(--border)", textDecoration: "none" }}>
              {user?.avatar ? (
                <img src={user.avatar} className="w-6 h-6 rounded-full object-cover shrink-0" alt="" />
              ) : (
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-black shrink-0" style={{ background: "var(--accent)", color: "#fff" }}>
                  {(user?.name || 'U')[0].toUpperCase()}
                </div>
              )}
              <span className="hidden sm:block text-[11px] font-bold" style={{ color: "var(--txt)" }}>Dashboard</span>
            </Link>
          ) : (
            <button onClick={onLoginClick} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold border transition-all hover:border-[var(--accent)]" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
              <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
              </svg>
              Sign In
            </button>
          )}
        </div>
      </header>

      {/* Custom Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-[9999] px-5 py-4 rounded-xl shadow-2xl flex items-center gap-3 transition-all duration-300 transform translate-y-0 opacity-100" style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)" }}>
          <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ background: "rgba(239,68,68,.15)" }}>
            <svg className="w-4 h-4 text-red-500" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
          </div>
          <div>
            <p className="text-[13px] font-bold tracking-tight">Access Denied</p>
            <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>{toast}</p>
          </div>
        </div>
      )}
    </>
  );
}
