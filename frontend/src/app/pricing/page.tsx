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
  Sparkles,
  Zap,
  Shield,
  ArrowRight,
  HelpCircle,
  Users,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

type BillingCycle = "monthly" | "annually";

interface PricingTier {
  id: "pro" | "team" | "enterprise";
  name: string;
  badge?: string;
  description: string;
  monthlyPrice: number;
  annualPrice: number;
  rowLimit: string;
  storageLimit: string;
  teamSeats: string;
  popular?: boolean;
  ctaText: string;
  highlights: string[];
}

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState<BillingCycle>("annually");
  const [launchModalOpen, setLaunchModalOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);
  const { user } = useAuth();

  const handleCtaClick = (action: "pro" | "team" | "enterprise") => {
    if (action === "pro" || action === "team") {
      window.location.href = `/billing/checkout?plan=${action}`;
    } else if (action === "enterprise") {
      window.location.href = "mailto:sales@dataforge.internal?subject=DataForge%20Enterprise%20Inquiry";
    }
  };

  // Exactly 3 Paid Tiers
  const paidTiers: PricingTier[] = [
    {
      id: "pro",
      name: "Pro Analyst",
      description: "For individual analysts & quants requiring relational joins & AutoML.",
      monthlyPrice: 29,
      annualPrice: 24,
      rowLimit: "1,000,000 Rows",
      storageLimit: "10 GB Cloud Storage",
      teamSeats: "Up to 5 team seats",
      ctaText: "Upgrade to Pro",
      highlights: [
        "1M rows out-of-core DuckDB streaming",
        "DuckDB Relational Join Studio (Inner/Left/Full)",
        "8 Enterprise Visualizations & Heatmaps",
        "Hypothesis Testing Suite (ANOVA, t-test, Chi-Sq)",
        "AutoML Tournament (LightGBM, XGBoost)",
        "Slide deck generator & presentation mode",
        "Priority email support",
      ],
    },
    {
      id: "team",
      name: "Team Collaboration",
      badge: "MOST POPULAR",
      popular: true,
      description: "For analytics teams needing cloud warehouses & shared governance.",
      monthlyPrice: 79,
      annualPrice: 69,
      rowLimit: "5,000,000 Rows",
      storageLimit: "50 GB Shared Storage",
      teamSeats: "Up to 25 team seats",
      ctaText: "Deploy Team Workspace",
      highlights: [
        "5M rows out-of-core streaming",
        "Live Warehouses (Snowflake, BigQuery, ClickHouse, Postgres)",
        "Multi-tenant team workspaces with 4-tier RBAC",
        "1-Click Exporter: dbt SQL models & Airflow DAGs",
        "Model Registry with online REST inference API",
        "Immutable governance audit logs & compliance trail",
        "Dedicated engineer support (4h SLA)",
      ],
    },
    {
      id: "enterprise",
      name: "Enterprise Scale",
      badge: "CUSTOM DEPLOYMENT",
      description: "For enterprises requiring high volume, private VPC, or air-gapped security.",
      monthlyPrice: 249,
      annualPrice: 199,
      rowLimit: "20,000,000+ Rows",
      storageLimit: "500 GB Organization Storage",
      teamSeats: "Unlimited team seats",
      ctaText: "Contact Solutions",
      highlights: [
        "20M+ rows or unlimited warehouse streaming",
        "Private VPC deployment or Zero Cloud Egress",
        "Enterprise SSO via SAML 2.0, Okta, & Azure AD",
        "Customer-Managed Encryption Keys (CMEK)",
        "Role-based column/row masking & dynamic PII scrubbing",
        "Custom Connector SDKs & dedicated SLA (99.99%)",
        "24/7 dedicated solutions architect",
      ],
    },
  ];

  const quickSpecs = [
    { spec: "Row Limit per Dataset", pro: "1,000,000", team: "5,000,000", enterprise: "20,000,000+" },
    { spec: "Cloud Storage Quota", pro: "10 GB", team: "50 GB", enterprise: "500 GB" },
    { spec: "Team Seats", pro: "Up to 5", team: "Up to 25", enterprise: "Unlimited" },
    { spec: "AutoML Jobs / Month", pro: "50 tournaments", team: "200 tournaments", enterprise: "1,000 tournaments" },
    { spec: "Cloud Warehouses & Lakehouses", pro: "Read-only dump", team: "Full live pushdown", enterprise: "Full live pushdown" },
    { spec: "1-Click Pipeline Exporters (dbt, Airflow)", pro: "Standard export", team: "Included", enterprise: "Included" },
    { spec: "Security & Governance", pro: "Standard RBAC", team: "4-Tier RBAC + Audit Logs", enterprise: "SAML SSO + CMEK + Air-Gap" },
    { spec: "Support SLA", pro: "Priority Email", team: "Dedicated Slack (4h SLA)", enterprise: "Dedicated Architect (99.99%)" },
  ];

  const faqs = [
    {
      q: "Can I get started completely free?",
      a: "Yes! Our Free Starter plan includes 100,000 rows, 500 MB storage, and 5 AutoML runs per month with zero credit card required.",
    },
    {
      q: "How does the annual billing discount work?",
      a: "When you select annual billing, you receive an automatic 20% discount on all plans, effectively giving you more than two months free every year.",
    },
    {
      q: "How do team seats work?",
      a: "Pro Analyst supports up to 5 collaborators. Team Collaboration supports up to 25 collaborators with 4-tier RBAC (Admin, Data Engineer, Analyst, Viewer). Enterprise Scale offers unlimited team seats.",
    },
    {
      q: "Does my data leave our network or get stored on external servers?",
      a: "For Pro and Team tiers, queries push down into your connected warehouse with secure credential encryption. For Enterprise Scale, DataForge can deploy 100% inside your private VPC with an absolute Zero Cloud Egress guarantee.",
    },
    {
      q: "Can I change or cancel my plan at any time?",
      a: "Yes. You can upgrade, downgrade, or cancel your subscription at any time with no lock-in or cancellation fees.",
    },
  ];

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

      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 pb-20">
        {/* Subtle Ambient Background Mesh */}
        <div className="noise" />
        <div className="mesh" />

        {/* Free Starter Callout Banner */}
        <div
          className="mb-10 p-3 sm:p-3.5 rounded-2xl border flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm transition-all"
          style={{
            background: "var(--card-bg)",
            borderColor: "var(--border)",
          }}
        >
          <div className="flex items-center gap-2.5 text-xs text-center sm:text-left">
            <span
              className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0"
              style={{
                background: "rgba(16, 185, 129, 0.12)",
                borderColor: "rgba(16, 185, 129, 0.3)",
                color: "#10b981",
              }}
            >
              Free Forever
            </span>
            <span style={{ color: "var(--txt)" }}>
              Solo analyst or student? Try our <strong style={{ color: "var(--txt)" }}>Free Starter</strong> plan (up to 100k rows, 500 MB storage).
            </span>
          </div>

          <button
            type="button"
            onClick={() => setLaunchModalOpen(true)}
            className="text-xs font-bold underline flex items-center gap-1 cursor-pointer shrink-0"
            style={{ color: "var(--accent)" }}
          >
            <span>Launch Free Workspace</span>
            <ArrowRight size={12} />
          </button>
        </div>

        {/* Header Block */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider mb-3 border border-[var(--border)] bg-[var(--card-bg)] text-[var(--accent)]">
            <Sparkles size={13} />
            <span>Transparent Pricing</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-black tracking-tight mb-3" style={{ color: "var(--txt)" }}>
            Predictable plans. Built for data teams.
          </h1>
          <p className="text-sm sm:text-base max-w-xl mx-auto" style={{ color: "var(--txt-m)" }}>
            Simple, honest pricing with out-of-core DuckDB performance. Choose the plan that fits your dataset volume.
          </p>

          {/* Billing Cycle Toggle */}
          <div className="inline-flex items-center gap-3 p-1 rounded-full border border-[var(--border)] bg-[var(--card-bg)] shadow-sm mt-6">
            <button
              type="button"
              onClick={() => setBillingCycle("monthly")}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                billingCycle === "monthly"
                  ? "bg-[var(--accent)] text-white shadow-md"
                  : "text-[var(--txt-m)] hover:text-[var(--txt)]"
              }`}
            >
              Monthly billing
            </button>
            <button
              type="button"
              onClick={() => setBillingCycle("annually")}
              className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                billingCycle === "annually"
                  ? "bg-[var(--accent)] text-white shadow-md"
                  : "text-[var(--txt-m)] hover:text-[var(--txt)]"
              }`}
            >
              <span>Annual billing</span>
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded-full border border-emerald-500/30">
                Save 20%
              </span>
            </button>
          </div>
        </div>

        {/* ── 3 PAID TIERS GRID ── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16 items-stretch">
          {paidTiers.map((tier) => {
            const price = billingCycle === "annually" ? tier.annualPrice : tier.monthlyPrice;

            return (
              <div
                key={tier.id}
                className={`relative rounded-3xl p-6 sm:p-7 flex flex-col justify-between border transition-all ${
                  tier.popular
                    ? "border-[var(--accent)] bg-[var(--card-bg)] shadow-2xl ring-2 ring-[var(--accent)]/30"
                    : "border-[var(--border)] bg-[var(--card-bg)] shadow-lg"
                }`}
              >
                {/* Popular Pill */}
                {tier.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-[var(--accent)] text-white shadow-md">
                    {tier.badge}
                  </div>
                )}

                <div>
                  <div className="mb-4">
                    <h3 className="text-xl font-bold mb-1" style={{ color: "var(--txt)" }}>
                      {tier.name}
                    </h3>
                    <p className="text-xs min-h-[34px]" style={{ color: "var(--txt-m)" }}>
                      {tier.description}
                    </p>
                  </div>

                  {/* Price */}
                  <div className="mb-5 pb-5 border-b" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl sm:text-5xl font-black" style={{ color: "var(--txt)" }}>
                        ${price}
                      </span>
                      <span className="text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
                        / month
                      </span>
                    </div>

                    <div className="flex flex-col gap-1 mt-3">
                      <span className="text-xs font-semibold" style={{ color: "var(--accent)" }}>
                        {tier.rowLimit} • {tier.storageLimit}
                      </span>
                      <span className="text-[11px] font-medium" style={{ color: "var(--txt-m)" }}>
                        {tier.teamSeats}
                      </span>
                    </div>
                  </div>

                  {/* Features list */}
                  <div className="space-y-2.5 mb-6">
                    <p className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                      Included Features:
                    </p>
                    {tier.highlights.map((feat, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs" style={{ color: "var(--txt)" }}>
                        <div className="w-4 h-4 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5 border border-emerald-500/30">
                          <Check size={10} strokeWidth={3} />
                        </div>
                        <span className="leading-tight">{feat}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* CTA Button */}
                <div>
                  <button
                    type="button"
                    onClick={() => handleCtaClick(tier.id)}
                    className={`w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                      tier.popular
                        ? "bg-[var(--accent)] text-white hover:opacity-95 shadow-lg shadow-[var(--accent)]/20"
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

        {/* ── CONCISE SPECS COMPARISON SUMMARY ── */}
        <div className="mb-16">
          <div className="text-center mb-8">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight" style={{ color: "var(--txt)" }}>
              Plan Specifications Comparison
            </h2>
            <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
              Transparent feature breakdown across the 3 paid tiers.
            </p>
          </div>

          <div
            className="rounded-2xl border overflow-hidden shadow-sm"
            style={{
              background: "var(--card-bg)",
              borderColor: "var(--border)",
            }}
          >
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr
                    className="border-b font-mono font-bold uppercase text-[10px] tracking-wider"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--txt-m)",
                    }}
                  >
                    <th className="p-3.5 sm:px-6">Capacity &amp; Engine</th>
                    <th className="p-3.5 text-center">Pro Analyst</th>
                    <th className="p-3.5 text-center" style={{ color: "var(--accent)" }}>Team Collaboration</th>
                    <th className="p-3.5 text-center">Enterprise Scale</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                  {quickSpecs.map((row, idx) => (
                    <tr
                      key={idx}
                      className="hover:bg-white/5 transition-colors"
                    >
                      <td className="p-3.5 sm:px-6 font-semibold" style={{ color: "var(--txt)" }}>
                        {row.spec}
                      </td>
                      <td className="p-3.5 text-center font-mono" style={{ color: "var(--txt-m)" }}>
                        {row.pro}
                      </td>
                      <td className="p-3.5 text-center font-mono font-bold" style={{ color: "var(--accent)" }}>
                        {row.team}
                      </td>
                      <td className="p-3.5 text-center font-mono" style={{ color: "var(--txt-m)" }}>
                        {row.enterprise}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ── CONCISE FAQ SECTION ── */}
        <div className="mb-16 max-w-3xl mx-auto">
          <div className="text-center mb-8">
            <div className="inline-flex items-center gap-1.5 text-xs font-mono font-bold uppercase tracking-wider mb-1" style={{ color: "var(--accent)" }}>
              <HelpCircle size={13} />
              <span>Questions &amp; Answers</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight" style={{ color: "var(--txt)" }}>
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-2.5">
            {faqs.map((faq, idx) => {
              const isOpen = expandedFaq === idx;
              return (
                <div
                  key={idx}
                  className="rounded-xl border transition-all overflow-hidden"
                  style={{
                    background: "var(--card-bg)",
                    borderColor: isOpen ? "var(--accent)" : "var(--border)",
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setExpandedFaq(isOpen ? null : idx)}
                    className="w-full p-4 text-left flex items-center justify-between gap-3 font-semibold text-xs sm:text-sm cursor-pointer"
                    style={{ color: "var(--txt)" }}
                  >
                    <span>{faq.q}</span>
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
                      className="px-4 pb-4 text-xs font-normal leading-relaxed border-t pt-2.5"
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

        {/* CTA Banner */}
        <CTABanner
          title="Ready to supercharge your data analysis?"
          subtitle="Ingest spreadsheets, relational databases, or cloud warehouses in seconds with out-of-core performance."
          buttonText="Launch Workspace Now"
          onAction={() => setLaunchModalOpen(true)}
        />
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
