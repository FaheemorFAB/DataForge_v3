"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import Header from "@/app/components/landing/Header";
import Footer from "@/app/components/landing/Footer";
import CTABanner from "@/app/components/landing/CTABanner";
import WorkspaceLaunchModal from "@/app/components/landing/WorkspaceLaunchModal";
import LoginModal from "@/app/components/landing/LoginModal";
import { useAuth } from "@/lib/auth";
import {
  Check,
  X,
  Sparkles,
  Zap,
  Shield,
  ArrowRight,
  HelpCircle,
  Users,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface PricingTier {
  id: "free" | "pro" | "team" | "enterprise";
  name: string;
  badge?: string;
  description: string;
  monthlyPrice: number;
  rowLimit: string;
  storageLimit: string;
  teamSeats: string;
  popular?: boolean;
  ctaText: string;
  highlights: string[];
  nonFeatures?: string[];
}

export default function PricingPage() {
  const [launchModalOpen, setLaunchModalOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);
  const [mobileFilter, setMobileFilter] = useState<"all" | "free" | "pro" | "team">("all");
  const [expandedCardFeatures, setExpandedCardFeatures] = useState<Record<string, boolean>>({});
  const { user } = useAuth();

  const handleCtaClick = (action: "free" | "pro" | "team" | "enterprise") => {
    if (action === "free") {
      setLaunchModalOpen(true);
    } else if (action === "pro" || action === "team") {
      window.location.href = `/billing/checkout?plan=${action}`;
    } else if (action === "enterprise") {
      window.location.href = "mailto:sales@dataforge.internal?subject=DataForge%20Enterprise%20Inquiry";
    }
  };

  const toggleCardFeatures = (id: string) => {
    setExpandedCardFeatures((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  // 3 Subscription Tiers: Free Starter, Pro Analyst, Team Collaboration
  const tiers: PricingTier[] = [
    {
      id: "free",
      name: "Free Starter",
      description: "For students, researchers & solo analysts exploring automated analytics in-browser.",
      monthlyPrice: 0,
      rowLimit: "25,000 Rows",
      storageLimit: "250 MB Storage",
      teamSeats: "1 solo user",
      ctaText: "Get Started Free",
      highlights: [
        "Data Ingestion: Local CSV, Excel & Google Sheets only",
        "Ingestion Limit: Capped at 25,000 rows / dataset (3 projects max)",
        "25,000 rows in-memory DuckDB processing",
        "1-Click automated data cleaning (nulls, duplicates, outliers)",
        "Automated statistical EDA reports & missing value heatmap",
        "Interactive chart builder (Bar, Line, Scatter, Box, Histogram)",
        "2-table relational join preview",
        "5 AutoML tournaments / month in workspace",
        "25 AI assistant natural-language queries / month",
        "In-browser exploratory workspace & profiling",
      ],
      nonFeatures: [
        "Unlimited data ingestion (Pro & Team only)",
        "OneDrive / Microsoft 365 Excel Online links",
        "Shared Database Connection Vault (SQL DBs)",
        "Dataset file exports & downloads (Locked in Free)",
        "Executive EDA presentation slides & Docker downloads",
      ],
    },
    {
      id: "pro",
      name: "Pro Analyst",
      description: "For solo data analysts & practitioners requiring advanced exports, EDA slides & AutoML Docker containers.",
      monthlyPrice: 29,
      rowLimit: "250,000 Rows / file",
      storageLimit: "5 GB Cloud Storage",
      teamSeats: "1 solo user",
      ctaText: "Upgrade to Pro Analyst",
      highlights: [
        "Unlimited Data Ingestion (upload & analyze as much as you need)",
        "250,000 rows processing with fast DuckDB streaming (10x Free)",
        "Cloud Storage: 5 GB workspace storage (20x Free)",
        "Ingestion Sources: Local CSV, Excel, Google Sheets & OneDrive/M365",
        "Full Dataset Downloads: CSV, Excel (.xlsx), Parquet & JSON",
        "Executive EDA presentation slides export (PowerPoint / PDF)",
        "AutoML production Docker containers (Dockerfile + inference API)",
        "Pipeline Code Export: Standalone Python & dbt SQL models",
        "Multi-table DuckDB Relational Join Studio",
        "50 AutoML tournaments / month (10x Free)",
        "250 AI natural-language queries / month (10x Free)",
        "Priority email support",
      ],
      nonFeatures: [
        "Shared Database Connection Vault (PostgreSQL, MySQL, SQLite, DuckDB)",
        "Apache Airflow production DAG exports & database push",
        "Multi-user team collaboration & 3-tier roles",
      ],
    },
    {
      id: "team",
      name: "Team Collaboration",
      badge: "MOST POPULAR",
      popular: true,
      description: "For analytics teams needing shared datasets, collaboration with 3 roles and database connections.",
      monthlyPrice: 79,
      rowLimit: "1,000,000 Rows / file",
      storageLimit: "25 GB Shared Storage",
      teamSeats: "Up to 5 team seats",
      ctaText: "Deploy Team Workspace",
      highlights: [
        "Multi-user team collaboration with 3 roles: Viewer, Analyst, Admin",
        "Up to 5 team member seats with role permissions",
        "Shared Database Connection Vault (PostgreSQL, MySQL, SQLite, DuckDB)",
        "1,000,000 rows processing with out-of-core streaming (4x Pro, 40x Free)",
        "25 GB shared organization cloud storage (5x Pro)",
        "Unlimited Team Data Ingestion & Pipeline Uploads",
        "Apache Airflow production DAG exports & pipeline code",
        "Direct Database Push & Cross-team exports",
        "Immutable team audit logs & compliance trail",
        "Secret link sharing (Restricted or Anyone with link)",
        "200 AutoML tournaments / month & Model Registry REST API (4x Pro)",
        "1,000 AI natural-language queries / month (4x Pro)",
        "Priority team support & onboarding",
      ],
      nonFeatures: [],
    },
  ];

  const quickSpecs = [
    { spec: "Data Ingestion Quota", free: "Capped (3 projects, 25K rows)", pro: "Unlimited Ingestion", team: "Unlimited Team Ingestion" },
    { spec: "Supported Sources", free: "Local CSV/Excel + Sheets only", pro: "Local, Sheets & OneDrive/M365", team: "All Sources + DB Connection Vault" },
    { spec: "Row Limit per Dataset", free: "25,000", pro: "250,000", team: "1,000,000" },
    { spec: "Cloud Storage Quota", free: "250 MB", pro: "5 GB", team: "25 GB" },
    { spec: "Team Seats & Roles", free: "1 solo user", pro: "1 solo user", team: "Up to 5 (Viewer, Analyst, Admin)" },
    { spec: "AutoML Tournaments", free: "5 / mo (in-app)", pro: "50 / mo + Docker", team: "200 / mo + Registry API" },
    { spec: "AI Natural Queries", free: "25 / mo", pro: "250 / mo", team: "1,000 / mo" },
    { spec: "DuckDB Join Canvas", free: "Up to 2 tables", pro: "Multi-table visual join", team: "Multi-table + Database joins" },
    { spec: "Exports & Deliverables", free: "Locked (In-browser only)", pro: "Full (CSV, XLSX, Parquet, Slides, Docker)", team: "All Pro + Airflow DAGs & DB Push" },
    { spec: "Security & Governance", free: "Local Workspace Auth", pro: "Encrypted Storage", team: "3-Tier Roles + Audit Logs" },
    { spec: "Support & SLA", free: "Community Docs", pro: "Priority Email", team: "Priority Team Support" },
  ];

  const faqs = [
    {
      q: "Can I get started completely free?",
      a: "Yes! Our Free Starter plan includes 25,000 rows, 250 MB storage, and 5 AutoML runs per month with zero credit card required. Note: File exports and model downloads are unlocked on Pro Analyst and Team Collaboration.",
    },
    {
      q: "How does monthly billing work?",
      a: "All DataForge subscriptions are billed monthly with zero long-term commitments via Dodo Payments, our global Merchant of Record. Invoices, sales tax, VAT, and card payments are handled securely. You can cancel anytime with 1-click.",
    },
    {
      q: "How do team seats work?",
      a: "Pro Analyst is designed for individual solo practitioners. Team Collaboration supports up to 5 team members with 3 clear roles: Admin, Analyst, and Viewer.",
    },
    {
      q: "Does my data leave our network or get stored on external servers?",
      a: "DataForge processes datasets locally or within your private instance with secure credential encryption and zero unauthorized data egress.",
    },
    {
      q: "Can I change or cancel my plan at any time?",
      a: "Yes. You can upgrade, downgrade, or cancel your subscription at any time with no lock-in or cancellation fees.",
    },
  ];

  const visibleTiers = tiers.filter((t) => {
    if (mobileFilter === "all") return true;
    return t.id === mobileFilter;
  });

  return (
    <div
      className="min-h-screen flex flex-col transition-colors duration-300 relative selection:bg-[var(--accent)] selection:text-white"
      style={{ background: "var(--bg)", color: "var(--txt)" }}
    >
      {/* Top Header */}
      <Header
        onLoginClick={() => setLoginModalOpen(true)}
        onLaunchWorkspace={() => setLaunchModalOpen(true)}
      />

      <main className="flex-1 max-w-6xl mx-auto w-full px-3 sm:px-6 lg:px-8 pt-6 sm:pt-12 pb-14 sm:pb-20">
        {/* Subtle Ambient Background Mesh */}
        <div className="noise" />
        <div className="mesh" />

        {/* Header Block */}
        <div className="text-center max-w-3xl mx-auto mb-8 sm:mb-12 px-2">
          <div
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-mono font-bold uppercase tracking-wider mb-3 border shadow-sm"
            style={{
              background: "rgba(255, 67, 16, 0.08)",
              borderColor: "rgba(255, 67, 16, 0.25)",
              color: "var(--accent)",
            }}
          >
            <Sparkles size={13} />
            <span>Simple &amp; Transparent</span>
          </div>
          <h1 className="text-2xl xs:text-3xl sm:text-4xl md:text-5xl font-black tracking-tight mb-2.5 sm:mb-3 leading-tight" style={{ color: "var(--txt)" }}>
            Predictable plans. Built for data teams.
          </h1>
          <p className="text-xs sm:text-sm md:text-base max-w-xl mx-auto leading-relaxed" style={{ color: "var(--txt-m)" }}>
            Simple, honest pricing with out-of-core DuckDB performance. Choose the plan that fits your dataset volume.
          </p>
        </div>

        {/* ── MOBILE PLAN SELECTOR TABS (< md) ── */}
        <div className="flex md:hidden items-center justify-center p-1 rounded-xl bg-[var(--surface)] border border-[var(--border)] max-w-xs sm:max-w-sm mx-auto mb-6 shadow-sm">
          <button
            type="button"
            onClick={() => setMobileFilter("all")}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all ${
              mobileFilter === "all"
                ? "bg-[var(--card-bg)] text-[var(--txt)] shadow-sm border border-[var(--border)]"
                : "text-[var(--txt-m)] hover:text-[var(--txt)]"
            }`}
          >
            All Plans
          </button>
          <button
            type="button"
            onClick={() => setMobileFilter("free")}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all ${
              mobileFilter === "free"
                ? "bg-emerald-600 text-white shadow-sm"
                : "text-[var(--txt-m)] hover:text-[var(--txt)]"
            }`}
          >
            Free ($0)
          </button>
          <button
            type="button"
            onClick={() => setMobileFilter("pro")}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all ${
              mobileFilter === "pro"
                ? "bg-[var(--accent)] text-white shadow-sm"
                : "text-[var(--txt-m)] hover:text-[var(--txt)]"
            }`}
          >
            Pro ($29)
          </button>
          <button
            type="button"
            onClick={() => setMobileFilter("team")}
            className={`flex-1 py-1.5 px-2 rounded-lg text-xs font-bold transition-all ${
              mobileFilter === "team"
                ? "bg-[var(--accent)] text-white shadow-sm"
                : "text-[var(--txt-m)] hover:text-[var(--txt)]"
            }`}
          >
            Team ($79)
          </button>
        </div>

        {/* ── 3 TIERS GRID (FREE, PRO, TEAM) ── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 lg:gap-6 mb-12 sm:mb-16 items-stretch max-w-6xl mx-auto">
          {visibleTiers.map((tier) => {
            const price = tier.monthlyPrice;
            const isExpanded = !!expandedCardFeatures[tier.id];
            const maxMobileHighlights = isExpanded ? tier.highlights.length : 5;

            return (
              <div
                key={tier.id}
                className={`relative rounded-2xl sm:rounded-3xl p-4 sm:p-6 lg:p-7 flex flex-col justify-between border transition-all ${
                  tier.popular
                    ? "border-[var(--accent)] bg-[var(--card-bg)] shadow-xl ring-2 ring-[var(--accent)]/30"
                    : "border-[var(--border)] bg-[var(--card-bg)] shadow-md"
                }`}
              >
                {/* Popular / Free Pill */}
                {tier.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-[var(--accent)] text-white shadow-md whitespace-nowrap z-10">
                    {tier.badge}
                  </div>
                )}
                {tier.id === "free" && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-600 text-white shadow-md whitespace-nowrap z-10">
                    100% Free
                  </div>
                )}

                <div>
                  <div className="mb-4">
                    <h3 className="text-lg sm:text-xl font-bold mb-1" style={{ color: "var(--txt)" }}>
                      {tier.name}
                    </h3>
                    <p className="text-xs min-h-0 sm:min-h-[36px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
                      {tier.description}
                    </p>
                  </div>

                  {/* Price */}
                  <div className="mb-4 pb-4 border-b" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl sm:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
                        ${price}
                      </span>
                      <span className="text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
                        {tier.id === "free" ? "forever" : "/ month"}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-md border" style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--accent)" }}>
                        {tier.rowLimit} • {tier.storageLimit}
                      </span>
                      <span className="text-[11px] font-medium opacity-80" style={{ color: "var(--txt-m)" }}>
                        {tier.teamSeats}
                      </span>
                    </div>
                  </div>

                  {/* Features list */}
                  <div className="space-y-2 mb-6">
                    {tier.id === "pro" && (
                      <div
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-bold mb-2.5 shadow-sm"
                        style={{
                          background: "var(--surface)",
                          borderColor: "var(--accent)",
                          color: "var(--accent)",
                        }}
                      >
                        <Sparkles size={12} className="shrink-0" />
                        <span>Everything in Free Starter, plus:</span>
                      </div>
                    )}
                    {tier.id === "team" && (
                      <div
                        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-bold mb-2.5 shadow-sm"
                        style={{
                          background: "var(--surface)",
                          borderColor: "var(--accent)",
                          color: "var(--accent)",
                        }}
                      >
                        <Sparkles size={12} className="shrink-0" />
                        <span>Everything in Pro Analyst, plus:</span>
                      </div>
                    )}

                    <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                      {tier.id === "free" ? "Included Features:" : "Tier Highlights:"}
                    </p>

                    {/* Desktop: shows all. Mobile: shows top 5 unless expanded */}
                    <div className="space-y-2">
                      {tier.highlights.map((feat, i) => {
                        const isHiddenOnMobile = i >= maxMobileHighlights;
                        return (
                          <div
                            key={i}
                            className={`items-start gap-2 text-xs ${
                              isHiddenOnMobile ? "hidden md:flex" : "flex"
                            }`}
                            style={{ color: "var(--txt)" }}
                          >
                            <div className="w-4 h-4 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5 border border-emerald-500/30">
                              <Check size={10} strokeWidth={3} />
                            </div>
                            <span className="leading-tight break-words">{feat}</span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Excluded Features with Cross Sign */}
                    {tier.nonFeatures && tier.nonFeatures.length > 0 && (
                      <div className={`pt-2 border-t border-[var(--border)]/50 space-y-2 ${isExpanded ? "block" : "hidden md:block"}`}>
                        {tier.nonFeatures.map((feat, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs opacity-50" style={{ color: "var(--txt-m)" }}>
                            <div className="w-4 h-4 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center shrink-0 mt-0.5 border border-red-500/25">
                              <X size={10} strokeWidth={2.5} />
                            </div>
                            <span className="leading-tight break-words">{feat}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Mobile toggle to expand all features */}
                    {tier.highlights.length > 5 && (
                      <button
                        type="button"
                        onClick={() => toggleCardFeatures(tier.id)}
                        className="md:hidden text-[11px] font-bold text-[var(--accent)] hover:underline pt-1 flex items-center gap-1 cursor-pointer"
                      >
                        {isExpanded ? (
                          <>
                            <span>Show fewer</span>
                            <ChevronUp size={12} />
                          </>
                        ) : (
                          <>
                            <span>+ {tier.highlights.length - 5} more features</span>
                            <ChevronDown size={12} />
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* CTA Button */}
                <div className="pt-2">
                  <button
                    type="button"
                    onClick={() => handleCtaClick(tier.id)}
                    className={`w-full py-3 px-4 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-md hover:scale-[1.01] active:scale-[0.99] ${
                      tier.popular
                        ? "bg-[var(--accent)] text-white hover:opacity-95 shadow-[var(--accent)]/20"
                        : tier.id === "free"
                          ? "bg-emerald-600 text-white hover:bg-emerald-500"
                          : "bg-[var(--border)] text-[var(--txt)] hover:bg-[var(--accent)] hover:text-white"
                    }`}
                  >
                    <span>{tier.ctaText}</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* ── MINIMAL INLINE CTA BANNER (Compact Shape) ── */}
        <div className="mb-12 sm:mb-16 max-w-4xl mx-auto px-1 sm:px-0">
          <CTABanner
            variant="compact"
            title="Test DataForge with your dataset"
            subtitle="Free plan — zero setup, instant automated EDA."
            buttonText="Launch Workspace"
            onAction={() => setLaunchModalOpen(true)}
            secondaryButtonText="Architecture"
            secondaryHref="/#about"
          />
        </div>

        {/* ── CONCISE SPECS COMPARISON SUMMARY ── */}
        <div className="mb-12 sm:mb-16">
          <div className="text-center mb-6 sm:mb-8 px-2">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight" style={{ color: "var(--txt)" }}>
              Plan Specifications Comparison
            </h2>
            <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
              Transparent feature breakdown across Free, Pro, and Team tiers.
            </p>
          </div>

          {/* Mobile swipe hint */}
          <div className="flex md:hidden items-center justify-between text-[11px] font-medium mb-2 px-1" style={{ color: "var(--txt-m)" }}>
            <span>Capacity &amp; Feature Matrix</span>
            <span className="flex items-center gap-1 text-[var(--accent)] font-semibold">
              Scroll horizontally <ArrowRight size={11} className="animate-pulse" />
            </span>
          </div>

          <div
            className="rounded-xl sm:rounded-2xl border overflow-hidden shadow-sm"
            style={{
              background: "var(--card-bg)",
              borderColor: "var(--border)",
            }}
          >
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full min-w-[580px] sm:min-w-full text-xs text-left border-collapse">
                <thead>
                  <tr
                    className="border-b font-mono font-bold uppercase text-[10px] tracking-wider"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--txt-m)",
                    }}
                  >
                    <th className="sticky left-0 z-20 p-3 sm:p-3.5 sm:px-6 min-w-[140px] sm:min-w-[180px] border-r border-[var(--border)] shadow-[2px_0_6px_rgba(0,0,0,0.06)]" style={{ background: "var(--surface)" }}>
                      Capacity &amp; Engine
                    </th>
                    <th className="p-3 sm:p-3.5 text-center text-emerald-400 min-w-[125px] sm:min-w-0">
                      <div>Free Starter</div>
                      <div className="text-[9px] opacity-75 font-normal tracking-normal">$0 / forever</div>
                    </th>
                    <th className="p-3 sm:p-3.5 text-center min-w-[125px] sm:min-w-0" style={{ color: "var(--txt)" }}>
                      <div>Pro Analyst</div>
                      <div className="text-[9px] opacity-75 font-normal tracking-normal">$29 / month</div>
                    </th>
                    <th className="p-3 sm:p-3.5 text-center min-w-[135px] sm:min-w-0" style={{ color: "var(--accent)" }}>
                      <div>Team Collaboration</div>
                      <div className="text-[9px] opacity-75 font-normal tracking-normal">$79 / month</div>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                  {quickSpecs.map((row, idx) => (
                    <tr
                      key={idx}
                      className="hover:bg-white/5 transition-colors"
                    >
                      <td
                        className="sticky left-0 z-10 p-3 sm:p-3.5 sm:px-6 font-semibold border-r border-[var(--border)] min-w-[140px] sm:min-w-[180px] shadow-[2px_0_6px_rgba(0,0,0,0.06)] transition-colors"
                        style={{
                          background: "var(--card-bg)",
                          color: "var(--txt)",
                        }}
                      >
                        {row.spec}
                      </td>
                      <td className="p-3 sm:p-3.5 text-center font-mono text-emerald-400">
                        {row.free}
                      </td>
                      <td className="p-3 sm:p-3.5 text-center font-mono" style={{ color: "var(--txt-m)" }}>
                        {row.pro}
                      </td>
                      <td className="p-3 sm:p-3.5 text-center font-mono font-bold" style={{ color: "var(--accent)" }}>
                        {row.team}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ── CONCISE FAQ SECTION ── */}
        <div className="mb-12 sm:mb-16 max-w-3xl mx-auto px-1 sm:px-0">
          <div className="text-center mb-6 sm:mb-8">
            <div className="inline-flex items-center gap-1.5 text-xs font-mono font-bold uppercase tracking-wider mb-1" style={{ color: "var(--accent)" }}>
              <HelpCircle size={13} />
              <span>Questions &amp; Answers</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight" style={{ color: "var(--txt)" }}>
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-2 sm:space-y-2.5">
            {faqs.map((faq, idx) => {
              const isOpen = expandedFaq === idx;
              return (
                <div
                  key={idx}
                  className="rounded-xl sm:rounded-2xl border transition-all overflow-hidden"
                  style={{
                    background: "var(--card-bg)",
                    borderColor: isOpen ? "var(--accent)" : "var(--border)",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setExpandedFaq(isOpen ? null : idx)}
                    className="w-full p-3.5 sm:p-4 text-left flex items-center justify-between gap-3 font-semibold text-xs sm:text-sm cursor-pointer"
                    style={{ color: "var(--txt)" }}
                  >
                    <span className="leading-snug">{faq.q}</span>
                    <div
                      className="w-5 h-5 rounded-full flex items-center justify-center shrink-0"
                      style={{
                        background: "var(--surface)",
                        color: isOpen ? "var(--accent)" : "var(--txt-m)",
                      }}
                    >
                      {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </div>
                  </button>
                  {isOpen && (
                    <div
                      className="px-3.5 pb-3.5 sm:px-4 sm:pb-4 text-xs font-normal leading-relaxed border-t pt-2.5"
                      style={{
                        borderColor: "var(--border)",
                        color: "var(--txt-m)",
                      }}
                    >
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

      </main>

      {/* Global Ingestion Hub Launch Modal */}
      <WorkspaceLaunchModal
        isOpen={launchModalOpen}
        onClose={() => setLaunchModalOpen(false)}
      />

      {/* Login Modal */}
      {loginModalOpen && (
        <LoginModal onClose={() => setLoginModalOpen(false)} />
      )}

      {/* Global Footer */}
      <Footer />
    </div>
  );
}
