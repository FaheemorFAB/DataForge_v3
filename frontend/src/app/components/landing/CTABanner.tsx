"use client";

import React from "react";
import Link from "next/link";
import { Sparkles, ArrowUpRight, UploadCloud } from "lucide-react";

interface CTABannerProps {
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  buttonText?: string;
  href?: string;
  bgColor?: string;
  btnTextColor?: string;
  onAction?: () => void;
}

export default function CTABanner({ title, subtitle, buttonText, href, bgColor, btnTextColor, onAction }: CTABannerProps) {
  const handleClick = () => {
    if (onAction) {
      onAction();
    } else if (!href) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <section className="py-20 border-t w-full" style={{ borderColor: "var(--border)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div
          className="relative rounded-3xl p-8 sm:p-12 md:p-16 border overflow-hidden backdrop-blur-2xl transition-all"
          style={{
            background: bgColor || "linear-gradient(135deg, rgba(255, 67, 16, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%), var(--card)",
            borderColor: "rgba(255, 67, 16, 0.3)",
            boxShadow: "0 20px 50px -10px rgba(0,0,0,0.4)",
          }}
        >
          {/* Ethereal background radial glow */}
          <div
            className="absolute -right-20 -bottom-20 w-80 h-80 rounded-full pointer-events-none blur-3xl opacity-30"
            style={{ background: "var(--accent)" }}
          />

          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
            <div className="space-y-3 max-w-2xl text-left">
              <div
                className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider border"
                style={{
                  background: "rgba(255, 67, 16, 0.08)",
                  borderColor: "rgba(255, 67, 16, 0.25)",
                  color: "var(--accent)",
                }}
              >
                <Sparkles size={12} />
                <span>Zero Latency Start</span>
              </div>
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
                {title || (
                  <>
                    Bring your dataset. <br className="hidden sm:inline" />
                    See it forged in seconds.
                  </>
                )}
              </h2>
              <p className="text-sm leading-relaxed" style={{ color: "var(--txt-m)" }}>
                {subtitle || "No credit card required. Pure automated analysis, instant EDA, and production ML models ready for download."}
              </p>
            </div>

            {href && !onAction ? (
              <Link
                href={href}
                className="flex items-center gap-2 px-6 py-3.5 rounded-xl text-xs font-bold text-white shadow-xl transition-all duration-200 hover:scale-[1.03] active:scale-[0.98]"
                style={{ background: "linear-gradient(135deg, var(--accent), #ff7043)" }}
              >
                <span>{buttonText || "Launch Workspace"}</span>
                <ArrowUpRight size={15} />
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleClick}
                className="flex items-center gap-2 px-6 py-3.5 rounded-xl text-xs font-bold text-white shadow-xl transition-all duration-200 hover:scale-[1.03] active:scale-[0.98] cursor-pointer"
                style={{ background: "linear-gradient(135deg, var(--accent), #ff7043)" }}
              >
                <UploadCloud size={16} />
                <span>{buttonText || "Launch Ingestion Hub"}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
