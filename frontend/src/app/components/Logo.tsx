import React from 'react';

interface LogoProps {
  size?: number;
  showText?: boolean;
  textSize?: number;
}

export default function Logo({ size = 28, showText = true, textSize = 22 }: LogoProps) {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <svg viewBox="0 0 64 64" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="df-logo-g" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#06B6D4" />
            <stop offset="52%" stopColor="#2563EB" />
            <stop offset="100%" stopColor="#4F46E5" />
          </linearGradient>
          <clipPath id="df-logo-c">
            <path d="M22,8 C52,8 56,20 56,32 C56,44 52,56 22,56 L13,56 Q10,56 10,52 L10,12 Q10,8 13,8 Z" />
          </clipPath>
        </defs>
        <path d="M22,8 C52,8 56,20 56,32 C56,44 52,56 22,56 L13,56 Q10,56 10,52 L10,12 Q10,8 13,8 Z" fill="url(#df-logo-g)" />
        <g clipPath="url(#df-logo-c)">
          <rect x="11" y="13" width="3" height="3" fill="#FFFFFF" opacity=".14" rx=".5" />
          <rect x="11" y="20" width="3" height="3" fill="#FFFFFF" opacity=".19" rx=".5" />
          <rect x="14.5" y="10" width="2.5" height="2.5" fill="#FFFFFF" opacity=".11" rx=".5" />
          <rect x="14.5" y="17" width="2.5" height="2.5" fill="#FFFFFF" opacity=".16" rx=".5" />
          <rect x="14.5" y="25" width="2.5" height="2.5" fill="#FFFFFF" opacity=".21" rx=".5" />
          <rect x="21" y="51.5" width="29" height="1.5" fill="#FFFFFF" opacity=".18" rx=".75" />
          <rect x="22" y="41" width="6" height="11" fill="#FFFFFF" opacity=".38" rx="1.5" />
          <rect x="31" y="31" width="6" height="21" fill="#FFFFFF" opacity=".54" rx="1.5" />
          <rect x="40" y="21" width="6" height="31" fill="#FFFFFF" opacity=".78" rx="1.5" />
          <rect x="47.5" y="27" width="5.5" height="25" fill="#FFFFFF" opacity=".60" rx="1.5" />
          <polyline points="25,41 34,31 43,21 50.25,27" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity=".88" />
          <circle cx="25" cy="41" r="2.5" fill="#FFFFFF" />
          <circle cx="34" cy="31" r="2.5" fill="#FFFFFF" />
          <circle cx="43" cy="21" r="2.5" fill="#FFFFFF" />
          <circle cx="50.25" cy="27" r="2.5" fill="#FFFFFF" />
        </g>
      </svg>
      {showText && (
        <div style={{ fontSize: textSize, fontFamily: "'Inter', -apple-system, sans-serif", fontWeight: 700, letterSpacing: "-.03em", lineHeight: 1, display: "flex", alignItems: "center" }}>
          <span style={{ color: "var(--txt)" }}>Data</span>
          <span style={{
            background: "linear-gradient(90deg, #06B6D4, #4F46E5)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            padding: "0.2em 0"
          }}>Forge</span>
        </div>
      )}
    </div>
  );
}
