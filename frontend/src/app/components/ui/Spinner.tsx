"use client";

import React from "react";
import Logo from "../Logo";

export interface SpinnerProps {
  /** Size variant or custom diameter in px */
  size?: "sm" | "md" | "lg" | "xl" | number;
  /** Visual variant: 'orbit' (dual concentric rings), 'ring' (minimalist arc), 'brand' (with Logo emblem) */
  variant?: "orbit" | "ring" | "brand";
  /** Optional title text displayed below spinner */
  label?: string;
  /** Optional subtitle or descriptive helper */
  description?: string;
  /** If true, wraps the spinner in a responsive full-height or full-viewport centered container */
  fullScreen?: boolean;
  /** Custom extra Tailwind classes for container */
  className?: string;
}

const SIZE_MAP = {
  sm: 18,
  md: 26,
  lg: 44,
  xl: 64,
};

export default function Spinner({
  size = "md",
  variant = "brand",
  label,
  description,
  fullScreen = false,
  className = "",
}: SpinnerProps) {
  const numericSize = typeof size === "number" ? size : SIZE_MAP[size] || 26;
  const isLarge = numericSize >= 40;

  const spinnerGraphic = (
    <div
      className="relative flex items-center justify-center shrink-0"
      style={{ width: numericSize, height: numericSize }}
    >
      {/* Outer Glow Aura */}
      <div
        className="absolute -inset-2 rounded-full opacity-30 blur-md pointer-events-none"
        style={{ background: "var(--glow, rgba(99, 102, 241, 0.25))" }}
      />

      {/* Outer Dashed Orbit */}
      <div
        className="absolute inset-0 rounded-full border-2 border-dashed animate-spin"
        style={{
          borderColor: "var(--accent, #6366f1)",
          animationDuration: "5s",
          boxShadow: "0 0 16px var(--glow, rgba(99, 102, 241, 0.35))",
        }}
      />

      {/* Inner Reverse Spinning Accent Arc */}
      <div
        className="absolute inset-1 rounded-full border-2 border-transparent border-t-emerald-400 border-r-emerald-400 animate-spin"
        style={{
          animationDuration: "1.8s",
          animationDirection: "reverse",
        }}
      />

      {/* Brand Logo Center (for larger spinners) */}
      {variant === "brand" && isLarge && (
        <div
          className="relative flex items-center justify-center rounded-xl p-1.5 shadow-md border backdrop-blur-sm"
          style={{
            background: "var(--surface, #ffffff)",
            borderColor: "var(--border, rgba(0,0,0,0.1))",
            boxShadow: "0 4px 12px var(--glow, rgba(0,0,0,0.08))",
          }}
        >
          <div className="animate-pulse flex items-center justify-center">
            <Logo size={Math.round(numericSize * 0.45)} showText={false} />
          </div>
        </div>
      )}

      {/* Center Ping Dot for smaller spinners */}
      {(!isLarge || variant !== "brand") && (
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0 animate-ping"
          style={{ background: "var(--accent, #6366f1)" }}
        />
      )}
    </div>
  );

  const content = (
    <div
      className={`flex flex-col items-center justify-center text-center px-4 py-6 ${className}`}
    >
      {spinnerGraphic}

      {(label || description) && (
        <div className="mt-4 space-y-1 max-w-sm sm:max-w-md mx-auto">
          {label && (
            <h3
              className="text-xs sm:text-sm md:text-base font-bold tracking-tight"
              style={{ color: "var(--txt, #0f172a)" }}
            >
              {label}
            </h3>
          )}
          {description && (
            <p
              className="text-[11px] sm:text-xs leading-relaxed max-w-xs sm:max-w-sm mx-auto"
              style={{ color: "var(--txt-m, #64748b)" }}
            >
              {description}
            </p>
          )}
        </div>
      )}
    </div>
  );

  if (fullScreen) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm animate-fadeIn"
        style={{ background: "var(--bg, #f8fafc)" }}
      >
        {content}
      </div>
    );
  }

  return content;
}
