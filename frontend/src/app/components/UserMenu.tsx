"use client";
import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { resolveAvatarUrl } from "@/lib/avatars";

export default function UserMenu() {
  const { user, loading, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [imgError, setImgError] = useState(false);

  if (loading || !user) return null;

  const avatarSrc = resolveAvatarUrl(user?.avatar);

  return (
    <div className="relative">
      <button 
        onClick={() => setIsMenuOpen(!isMenuOpen)} 
        className="flex items-center gap-1.5 p-1 rounded-full border transition-all hover:border-[var(--accent)]" 
        style={{ borderColor: "var(--border)" }}
        title={user?.name || "User Account"}
      >
        {!imgError && avatarSrc ? (
          <img
            src={avatarSrc}
            className="w-7 h-7 rounded-full object-cover shrink-0"
            alt={user?.name || "User"}
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-black shrink-0" style={{ background: "var(--accent)", color: "#fff" }}>
            {(user?.name || 'U')[0].toUpperCase()}
          </div>
        )}
        <svg className="w-3.5 h-3.5 mr-0.5 opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
      </button>

      {isMenuOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsMenuOpen(false)}></div>
          <div className="absolute right-0 mt-2 w-48 rounded-xl shadow-2xl py-1.5 z-50 overflow-hidden border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <Link href="/dashboard" className="flex items-center px-4 py-2.5 text-[12px] font-bold hover:bg-black/5 dark:hover:bg-white/5 transition-colors" style={{ color: "var(--txt)", textDecoration: "none" }} onClick={() => setIsMenuOpen(false)}>
              <svg className="w-3.5 h-3.5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>
              Dashboard
            </Link>
            <button onClick={() => { setIsMenuOpen(false); logout(); }} className="w-full flex items-center px-4 py-2.5 text-[12px] font-bold hover:bg-black/5 dark:hover:bg-white/5 transition-colors text-left text-red-500">
              <svg className="w-3.5 h-3.5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
              Logout
            </button>
          </div>
        </>
      )}
    </div>
  );
}
