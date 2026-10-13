import React from "react";

interface LogoProps {
  size?: number;
  className?: string;
}

export function SupabaseLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 109 113" fill="none" className={className}>
      <path
        d="M63.7076 110.284C60.9181 114.076 54.8398 112.242 54.6759 107.564L52.8859 56.6667H97.6974C104.305 56.6667 108.069 64.3312 103.882 69.4582L63.7076 110.284Z"
        fill="#3ECF8E"
      />
      <path
        d="M45.2924 2.71632C48.0819 -1.07629 54.1602 0.758066 54.3241 5.43576L55.8859 56.3333H11.3026C4.69532 56.3333 0.930966 48.6688 5.11794 43.5418L45.2924 2.71632Z"
        fill="#249361"
      />
    </svg>
  );
}

export function PostgresLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#336791" fillOpacity="0.15" stroke="#336791" strokeWidth="2" />
      <path
        d="M24 10C16.8 10 13 15 13 22C13 28.5 16.5 32 20.5 33V37C20.5 37.6 21 38 21.6 38H24C24.6 38 25 37.6 25 37V33C25 31.5 26 31 27 30C29.5 27.5 31 24.5 31 21C31 14.5 28 10 24 10Z"
        fill="#336791"
      />
      <circle cx="20" cy="18" r="2" fill="#FFFFFF" />
      <path d="M29 22C31 22 34 24 35 27C34 28 32 29 29.5 28.5" stroke="#336791" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function MySQLLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#00758F" fillOpacity="0.15" stroke="#00758F" strokeWidth="2" />
      <path
        d="M36 26C33 21 28 16 20 16C16 16 13 18 12 21C11.5 22.5 12 24.5 13.5 25.5C15.5 27 18.5 26.5 21 26C25.5 25 29 27 31 30C33 33 32 35 30 36C27 37.5 23 36 21 34"
        stroke="#00758F"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <circle cx="16" cy="20" r="1.8" fill="#F29111" />
      <path d="M35 24L38 21M38 26L41 24" stroke="#F29111" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function SnowflakeLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#29B5E8" fillOpacity="0.15" stroke="#29B5E8" strokeWidth="2" />
      <path
        d="M24 8V40M10 16L38 32M10 32L38 16M24 13L21 16M24 13L27 16M24 35L21 32M24 35L27 32M14 18L18 18M14 18L16 21M34 30L30 30M34 30L32 27M14 30L18 30M14 30L16 27M34 18L30 18M34 18L32 21"
        stroke="#29B5E8"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function BigQueryLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#4285F4" fillOpacity="0.15" stroke="#4285F4" strokeWidth="2" />
      <path
        d="M17 14L24 10L31 14V22L24 26L17 22V14Z"
        fill="#4285F4"
        fillOpacity="0.8"
      />
      <path
        d="M24 26L31 22V30L24 34L17 30V22L24 26Z"
        stroke="#4285F4"
        strokeWidth="2"
      />
      <circle cx="31" cy="31" r="5" fill="#34A853" fillOpacity="0.2" stroke="#34A853" strokeWidth="2" />
      <path d="M35 35L40 40" stroke="#EA4335" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function ClickHouseLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#FCA311" fillOpacity="0.15" stroke="#FCA311" strokeWidth="2" />
      <rect x="12" y="16" width="3" height="16" rx="1.5" fill="#FF4D4D" />
      <rect x="17" y="12" width="3" height="24" rx="1.5" fill="#FFA500" />
      <rect x="22" y="18" width="3" height="12" rx="1.5" fill="#FFD700" />
      <rect x="27" y="10" width="3" height="28" rx="1.5" fill="#FFA500" />
      <rect x="32" y="15" width="3" height="18" rx="1.5" fill="#FF4D4D" />
    </svg>
  );
}

export function SQLiteLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#003B57" fillOpacity="0.15" stroke="#003B57" strokeWidth="2" />
      <ellipse cx="24" cy="15" rx="12" ry="5" fill="#0EA5E9" fillOpacity="0.7" />
      <path d="M12 15V24C12 26.8 17.4 29 24 29C30.6 29 36 26.8 36 24V15" stroke="#0EA5E9" strokeWidth="2" />
      <path d="M12 24V33C12 35.8 17.4 38 24 38C30.6 38 36 35.8 36 33V24" stroke="#0EA5E9" strokeWidth="2" />
      <path d="M22 21L26 27M26 21L22 27" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function MongoDBLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#13AA52" fillOpacity="0.15" stroke="#13AA52" strokeWidth="2" />
      <path
        d="M24 8C24 8 16 15 16 25C16 31 19.5 36 24 40C28.5 36 32 31 32 25C32 15 24 8 24 8Z"
        fill="#13AA52"
        fillOpacity="0.85"
      />
      <path d="M24 10V39" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function NeonLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#00E599" fillOpacity="0.15" stroke="#00E599" strokeWidth="2" />
      <path
        d="M24 10L36 34H12L24 10Z"
        stroke="#00E599"
        strokeWidth="3"
        strokeLinejoin="round"
        fill="#00E599"
        fillOpacity="0.25"
      />
      <circle cx="24" cy="26" r="3" fill="#00E599" />
    </svg>
  );
}

export function JSONLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <rect x="4" y="4" width="40" height="40" rx="12" fill="#F59E0B" fillOpacity="0.15" stroke="#F59E0B" strokeWidth="2" />
      <text
        x="24"
        y="21"
        textAnchor="middle"
        fontFamily="monospace"
        fontWeight="900"
        fontSize="15"
        fill="#F59E0B"
      >
        &#123; &#125;
      </text>
      <text
        x="24"
        y="34"
        textAnchor="middle"
        fontFamily="monospace"
        fontWeight="800"
        fontSize="10"
        letterSpacing="0.1em"
        fill="#F59E0B"
      >
        JSON
      </text>
    </svg>
  );
}

export function GoogleSheetsLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <rect x="8" y="6" width="32" height="36" rx="6" fill="#0F9D58" />
      <path d="M30 6L40 16H30V6Z" fill="#87CEAB" />
      <rect x="14" y="20" width="20" height="16" rx="2" fill="#FFFFFF" fillOpacity="0.9" />
      <line x1="14" y1="28" x2="34" y2="28" stroke="#0F9D58" strokeWidth="1.5" />
      <line x1="24" y1="20" x2="24" y2="36" stroke="#0F9D58" strokeWidth="1.5" />
    </svg>
  );
}

export function DatabricksLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#FF3621" fillOpacity="0.12" stroke="#FF3621" strokeWidth="1.5" />
      <path
        d="M24 10L36 17L24 24L12 17L24 10Z"
        fill="#FF3621"
      />
      <path
        d="M12 21L24 28L36 21L33 19.5L24 24.5L15 19.5L12 21Z"
        fill="#FF3621"
      />
      <path
        d="M12 26L24 33L36 26L33 24.5L24 29.5L15 24.5L12 26Z"
        fill="#FF3621"
      />
      <path
        d="M12 31L24 38L36 31L33 29.5L24 34.5L15 29.5L12 31Z"
        fill="#FF3621"
      />
    </svg>
  );
}

export function AWSS3Logo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <rect x="6" y="8" width="36" height="32" rx="8" fill="#FF9900" fillOpacity="0.12" stroke="#FF9900" strokeWidth="1.5" />
      <path
        d="M14 16H34M14 24H34M14 32H34"
        stroke="#FF9900"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
      <circle cx="18" cy="16" r="2" fill="#FF9900" />
      <circle cx="18" cy="24" r="2" fill="#FF9900" />
      <circle cx="18" cy="32" r="2" fill="#FF9900" />
    </svg>
  );
}

export function GCSLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#4285F4" fillOpacity="0.12" stroke="#4285F4" strokeWidth="1.5" />
      <rect x="14" y="14" width="20" height="20" rx="4" fill="#4285F4" />
      <circle cx="24" cy="24" r="5" fill="#FFFFFF" />
      <circle cx="24" cy="24" r="2" fill="#4285F4" />
    </svg>
  );
}

export function AzureBlobLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <circle cx="24" cy="24" r="22" fill="#0078D4" fillOpacity="0.12" stroke="#0078D4" strokeWidth="1.5" />
      <path
        d="M15 34L26 12L31 22L20 34H15Z"
        fill="#0078D4"
      />
      <path
        d="M27 22L21 34H33L31 29L27 22Z"
        fill="#50E6FF"
      />
    </svg>
  );
}

export function CSVLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <rect x="10" y="8" width="28" height="32" rx="6" fill="#10B981" fillOpacity="0.15" stroke="#10B981" strokeWidth="1.5" />
      <rect x="15" y="14" width="18" height="8" rx="2" fill="#10B981" />
      <text x="24" y="20.5" textAnchor="middle" fill="#FFFFFF" fontSize="6.5" fontWeight="900" fontFamily="sans-serif">CSV</text>
      <line x1="16" y1="27" x2="32" y2="27" stroke="#10B981" strokeWidth="2" strokeLinecap="round" />
      <line x1="16" y1="32" x2="28" y2="32" stroke="#10B981" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function ExcelLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <rect x="10" y="8" width="28" height="32" rx="6" fill="#107C41" fillOpacity="0.15" stroke="#107C41" strokeWidth="1.5" />
      <rect x="12" y="16" width="16" height="16" rx="3" fill="#107C41" />
      <text x="20" y="28" textAnchor="middle" fill="#FFFFFF" fontSize="12" fontWeight="900" fontFamily="sans-serif">X</text>
      <line x1="31" y1="18" x2="36" y2="18" stroke="#107C41" strokeWidth="2" strokeLinecap="round" />
      <line x1="31" y1="24" x2="36" y2="24" stroke="#107C41" strokeWidth="2" strokeLinecap="round" />
      <line x1="31" y1="30" x2="36" y2="30" stroke="#107C41" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function ParquetLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <rect x="8" y="8" width="32" height="32" rx="8" fill="#0284C7" fillOpacity="0.15" stroke="#0284C7" strokeWidth="1.5" />
      <rect x="14" y="14" width="8" height="9" rx="2" fill="#38BDF8" />
      <rect x="26" y="14" width="8" height="9" rx="2" fill="#0284C7" />
      <rect x="14" y="25" width="8" height="9" rx="2" fill="#0284C7" />
      <rect x="26" y="25" width="8" height="9" rx="2" fill="#38BDF8" />
    </svg>
  );
}


export function MicrosoftExcelOnlineLogo({ size = 24, className = "" }: LogoProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" className={className}>
      <rect x="8" y="8" width="32" height="32" rx="8" fill="#107C41" fillOpacity="0.15" stroke="#107C41" strokeWidth="1.5" />
      <rect x="11" y="14" width="18" height="20" rx="3" fill="#107C41" />
      <text x="20" y="28.5" textAnchor="middle" fill="#FFFFFF" fontSize="13" fontWeight="900" fontFamily="sans-serif">X</text>
      <circle cx="34" cy="17" r="2.2" fill="#22C55E" />
      <line x1="31" y1="24" x2="37" y2="24" stroke="#107C41" strokeWidth="2.5" strokeLinecap="round" />
      <line x1="31" y1="30" x2="37" y2="30" stroke="#107C41" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

