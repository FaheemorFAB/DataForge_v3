"use client";

import React, { useState } from "react";
import Link from "next/link";
import ThemeSwitcher from "../ThemeSwitcher";
import Logo from "../Logo";
import { useAuth } from "@/lib/auth";
import UserMenu from "../UserMenu";
import { LogIn, Menu, X, ArrowRight, Zap } from "lucide-react";

interface HeaderProps {
  onLoginClick: () => void;
  onLaunchWorkspace?: () => void;
}

export default function Header({ onLoginClick, onLaunchWorkspace }: HeaderProps) {
  const { user, loading: authLoading } = useAuth();
  const isLoggedIn = !!user;
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: "Pipeline", href: "/#pipeline" },
    { label: "Users", href: "/#audiences" },
    { label: "Architecture", href: "/#platform-architecture" },
    { label: "About", href: "/#origin" },
    { label: "Team", href: "/#meet-the-builders" },
  ];

  const handleLaunch = () => {
    if (onLaunchWorkspace) {
      onLaunchWorkspace();
    } else {
      onLoginClick();
    }
  };

  return (
    <header
      className="sticky top-0 z-50 w-full backdrop-blur-xl border-b transition-colors duration-300"
      style={{
        background: "var(--nav)",
        borderColor: "var(--border)",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo without version pill */}
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 group">
            <Logo size={28} textSize={19} />
          </Link>
        </div>

        {/* Desktop Navigation links */}
        <nav className="hidden md:flex items-center gap-4 lg:gap-6 text-xs font-semibold">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              className="transition-colors hover:text-[var(--accent)]"
              style={{ color: "var(--txt-m)" }}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Right CTA / Theme / Auth */}
        <div className="flex items-center gap-2.5 sm:gap-3">
          <ThemeSwitcher />

          {/* Solid Non-Gradient Pricing CTA Button */}
          <Link
            href="/pricing"
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-bold transition-all duration-200 hover:opacity-90 active:scale-[0.98]"
            style={{
              background: "var(--accent)",
              color: "#ffffff",
              boxShadow: "0 2px 8px var(--glow)",
            }}
          >
            <span>Pricing</span>
          </Link>

          {!authLoading && isLoggedIn ? (
            <UserMenu />
          ) : (
            <button
              onClick={onLoginClick}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all duration-200 hover:scale-[1.02] hover:border-orange-500/50"
              style={{
                background: "rgba(255, 255, 255, 0.04)",
                borderColor: "var(--border)",
                color: "var(--txt)",
              }}
            >
              <LogIn size={13} style={{ color: "var(--accent)" }} />
              <span>Sign In</span>
            </button>
          )}

          {/* Mobile hamburger button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-2 rounded-xl border transition-colors"
            style={{
              borderColor: "var(--border)",
              color: "var(--txt-m)",
              background: "var(--card-bg, transparent)",
            }}
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {mobileMenuOpen && (
        <div
          className="md:hidden border-b px-5 py-4 space-y-3 transition-all backdrop-blur-2xl"
          style={{
            background: "var(--nav)",
            borderColor: "var(--border)",
          }}
        >
          <Link
            href="/pricing"
            onClick={() => setMobileMenuOpen(false)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all mb-2"
            style={{
              background: "var(--accent)",
              color: "#ffffff",
            }}
          >
            <span>Pricing</span>
          </Link>

          <div className="flex flex-col space-y-2">
            {navLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="px-3 py-2 rounded-lg text-sm font-semibold transition-colors hover:bg-orange-500/10 hover:text-[var(--accent)] flex items-center justify-between"
                style={{ color: "var(--txt)" }}
              >
                <span>{link.label}</span>
                <ArrowRight size={14} style={{ color: "var(--accent)" }} />
              </Link>
            ))}
          </div>

          {!authLoading && !isLoggedIn && (
            <div className="pt-2 border-t" style={{ borderColor: "var(--border)" }}>
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  onLoginClick();
                }}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold border"
                style={{
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                  background: "var(--card-bg)",
                }}
              >
                <LogIn size={14} style={{ color: "var(--accent)" }} />
                <span>Sign In to DataForge</span>
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
