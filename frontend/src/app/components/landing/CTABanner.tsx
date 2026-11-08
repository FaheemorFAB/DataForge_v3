"use client";

import React from "react";
import Link from "next/link";
import { Sparkles, ArrowUpRight, UploadCloud, ArrowRight, Check, LucideIcon } from "lucide-react";

export type CTABannerVariant = "default" | "centered" | "compact" | "card";

export interface CTABannerProps {
  variant?: CTABannerVariant;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  badge?: string;
  buttonText?: string;
  href?: string;
  bgColor?: string;
  btnTextColor?: string;
  onAction?: () => void;
  secondaryButtonText?: string;
  secondaryHref?: string;
  onSecondaryAction?: () => void;
  perks?: string[];
  icon?: LucideIcon;
  className?: string;
  containerClassName?: string;
  noBorderTop?: boolean;
}

export default function CTABanner({
  variant = "default",
  title,
  subtitle,
  badge,
  buttonText,
  href,
  bgColor,
  btnTextColor,
  onAction,
  secondaryButtonText,
  secondaryHref,
  onSecondaryAction,
  perks,
  icon: CustomIcon,
  className = "",
  containerClassName = "",
  noBorderTop = false,
}: CTABannerProps) {
  const handleClick = () => {
    if (onAction) {
      onAction();
    } else if (!href) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleSecondaryClick = () => {
    if (onSecondaryAction) {
      onSecondaryAction();
    }
  };

  const ActionIcon = CustomIcon || (href ? ArrowUpRight : UploadCloud);

  const defaultBackground =
    bgColor ||
    "linear-gradient(135deg, rgba(255, 67, 16, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%), var(--card)";

  const renderPrimaryButton = (sizeClass = "px-6 py-3.5 text-xs") => {
    const content = (
      <>
        <span>{buttonText || (href ? "Launch Workspace" : "Launch Ingestion Hub")}</span>
        <ActionIcon size={15} />
      </>
    );

    const buttonStyle = {
      background: "linear-gradient(135deg, var(--accent), #ff7043)",
      color: btnTextColor || "#ffffff",
    };

    if (href && !onAction) {
      return (
        <Link
          href={href}
          className={`flex items-center justify-center gap-2 rounded-xl font-bold shadow-xl transition-all duration-200 hover:scale-[1.03] active:scale-[0.98] ${sizeClass}`}
          style={buttonStyle}
        >
          {content}
        </Link>
      );
    }

    return (
      <button
        type="button"
        onClick={handleClick}
        className={`flex items-center justify-center gap-2 rounded-xl font-bold shadow-xl transition-all duration-200 hover:scale-[1.03] active:scale-[0.98] cursor-pointer ${sizeClass}`}
        style={buttonStyle}
      >
        {content}
      </button>
    );
  };

  const renderSecondaryButton = (sizeClass = "px-5 py-3 text-xs") => {
    if (!secondaryButtonText) return null;

    const content = (
      <>
        <span>{secondaryButtonText}</span>
        <ArrowRight size={14} />
      </>
    );

    const buttonStyle = {
      background: "var(--card-bg)",
      borderColor: "var(--border)",
      color: "var(--txt)",
    };

    if (secondaryHref && !onSecondaryAction) {
      return (
        <Link
          href={secondaryHref}
          className={`flex items-center justify-center gap-2 rounded-xl font-bold border transition-all duration-200 hover:border-[var(--accent)] active:scale-[0.98] ${sizeClass}`}
          style={buttonStyle}
        >
          {content}
        </Link>
      );
    }

    return (
      <button
        type="button"
        onClick={handleSecondaryClick}
        className={`flex items-center justify-center gap-2 rounded-xl font-bold border transition-all duration-200 hover:border-[var(--accent)] active:scale-[0.98] cursor-pointer ${sizeClass}`}
        style={buttonStyle}
      >
        {content}
      </button>
    );
  };

  /* ─────────────────────────────────────────────────────────────
     VARIANT: COMPACT (Slim inline callout bar - Fully Responsive)
  ───────────────────────────────────────────────────────────── */
  if (variant === "compact") {
    return (
      <div className={`w-full ${containerClassName}`}>
        <div
          className={`relative rounded-2xl p-4 sm:p-6 border overflow-hidden backdrop-blur-xl transition-all ${className}`}
          style={{
            background: defaultBackground,
            borderColor: "rgba(255, 67, 16, 0.25)",
            boxShadow: "0 10px 30px -10px rgba(0,0,0,0.3)",
          }}
        >
          <div
            className="absolute -right-10 -bottom-10 w-44 h-44 rounded-full pointer-events-none blur-2xl opacity-25"
            style={{ background: "var(--accent)" }}
          />

          <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 sm:gap-6">
            <div className="flex items-start sm:items-center gap-3 text-left min-w-0 flex-1 w-full md:w-auto">
              <div
                className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0 border shadow-inner mt-0.5 sm:mt-0"
                style={{
                  background: "var(--card-bg)",
                  borderColor: "var(--border)",
                  color: "var(--accent)",
                }}
              >
                <ActionIcon size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm sm:text-base md:text-lg font-bold tracking-tight leading-snug break-words" style={{ color: "var(--txt)" }}>
                  {title || "Ready to experience DataForge?"}
                </h3>
                {subtitle && (
                  <p className="text-xs sm:text-sm font-normal text-[var(--txt-m)] mt-1 leading-relaxed break-words">
                    {subtitle}
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full md:w-auto shrink-0 pt-1 md:pt-0">
              {renderSecondaryButton("w-full sm:w-auto px-4 py-2.5 sm:py-2 text-xs text-center justify-center")}
              {renderPrimaryButton("w-full sm:w-auto px-5 py-2.5 sm:py-2 text-xs text-center justify-center")}
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ─────────────────────────────────────────────────────────────
     VARIANT: CENTERED (High-impact showcase with optional perks)
  ───────────────────────────────────────────────────────────── */
  if (variant === "centered") {
    return (
      <section
        className={`py-16 sm:py-20 w-full ${!noBorderTop ? "border-t" : ""} ${containerClassName}`}
        style={{ borderColor: "var(--border)" }}
      >
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div
            className={`relative rounded-3xl p-8 sm:p-12 md:p-16 border overflow-hidden backdrop-blur-2xl text-center flex flex-col items-center justify-center transition-all ${className}`}
            style={{
              background: defaultBackground,
              borderColor: "rgba(255, 67, 16, 0.35)",
              boxShadow: "0 25px 60px -15px rgba(0,0,0,0.45)",
            }}
          >
            {/* Center radiant glow */}
            <div
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full pointer-events-none blur-3xl opacity-20"
              style={{ background: "var(--accent)" }}
            />

            <div className="relative z-10 flex flex-col items-center max-w-3xl mx-auto">
              <h2
                className="text-2xl sm:text-3xl md:text-5xl font-black tracking-tight leading-tight mb-4"
                style={{ color: "var(--txt)" }}
              >
                {title || (
                  <>
                    Bring your dataset. <br />
                    See it forged in seconds.
                  </>
                )}
              </h2>

              {subtitle && (
                <p
                  className="text-sm sm:text-base leading-relaxed max-w-xl mx-auto mb-8 font-normal"
                  style={{ color: "var(--txt-m)" }}
                >
                  {subtitle}
                </p>
              )}

              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full sm:w-auto">
                {renderPrimaryButton("px-7 py-3.5 text-sm")}
                {renderSecondaryButton("px-6 py-3.5 text-sm")}
              </div>

              {perks && perks.length > 0 && (
                <div
                  className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 mt-8 pt-6 border-t w-full max-w-lg"
                  style={{ borderColor: "var(--border)" }}
                >
                  {perks.map((perk, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
                      <Check size={14} style={{ color: "var(--accent)" }} />
                      <span>{perk}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    );
  }

  /* ─────────────────────────────────────────────────────────────
     VARIANT: CARD (Contained floating card)
  ───────────────────────────────────────────────────────────── */
  if (variant === "card") {
    return (
      <div
        className={`relative rounded-2xl p-6 sm:p-8 border overflow-hidden backdrop-blur-xl flex flex-col gap-4 text-left ${className}`}
        style={{
          background: defaultBackground,
          borderColor: "rgba(255, 67, 16, 0.3)",
          boxShadow: "0 15px 40px -10px rgba(0,0,0,0.35)",
        }}
      >
        <div
          className="absolute -top-10 -right-10 w-36 h-36 rounded-full pointer-events-none blur-2xl opacity-20"
          style={{ background: "var(--accent)" }}
        />

        <div className="relative z-10 flex flex-col gap-3">
          <h3 className="text-xl sm:text-2xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
            {title || "Start Your Workspace"}
          </h3>
          {subtitle && (
            <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--txt-m)" }}>
              {subtitle}
            </p>
          )}

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 pt-2">
            {renderPrimaryButton("px-5 py-3 text-xs w-full sm:w-auto")}
            {renderSecondaryButton("px-4 py-3 text-xs w-full sm:w-auto")}
          </div>
        </div>
      </div>
    );
  }

  /* ─────────────────────────────────────────────────────────────
     VARIANT: DEFAULT (Horizontal hero banner at section ends)
  ───────────────────────────────────────────────────────────── */
  return (
    <section
      className={`py-20 w-full ${!noBorderTop ? "border-t" : ""} ${containerClassName}`}
      style={{ borderColor: "var(--border)" }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div
          className={`relative rounded-3xl p-8 sm:p-12 md:p-16 border overflow-hidden backdrop-blur-2xl transition-all ${className}`}
          style={{
            background: defaultBackground,
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
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
                {title || (
                  <>
                    Bring your dataset. <br className="hidden sm:inline" />
                    See it forged in seconds.
                  </>
                )}
              </h2>
              <p className="text-sm leading-relaxed" style={{ color: "var(--txt-m)" }}>
                {subtitle ||
                  "No credit card required. Pure automated analysis, instant EDA, and production ML models ready for download."}
              </p>

              {perks && perks.length > 0 && (
                <div className="flex flex-wrap items-center gap-4 pt-2">
                  {perks.map((perk, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--txt-m)" }}>
                      <Check size={13} style={{ color: "var(--accent)" }} />
                      <span>{perk}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
              {renderSecondaryButton()}
              {renderPrimaryButton()}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
