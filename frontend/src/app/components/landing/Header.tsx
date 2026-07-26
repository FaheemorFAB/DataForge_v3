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

  return (
    <header className="px-5 md:px-8 py-4 flex justify-between items-center border-b sticky top-0 z-50 backdrop-blur-md" style={{ background: "var(--nav)", borderColor: "var(--border)" }}>
      <div className="flex items-center gap-3">
        <Logo />
      </div>
      <div className="flex items-center gap-3">
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
  );
}
