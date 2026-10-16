"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Check, Sparkles, ArrowRight } from "lucide-react";

interface Props {
  onSelectPlan: (plan: string) => void;
}

export default function HomepagePricingSection({ onSelectPlan }: Props) {
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annually">("annually");

  // Exactly 3 Paid Tiers
  const plans = [
    {
      id: "pro",
      name: "Pro Analyst",
      badge: "MOST POPULAR",
      description: "For professional data analysts, quants, and high-velocity business teams.",
      price: 29,
      annualPrice: 24,
      limits: "Up to 1,000,000 rows • 10 GB storage",
      seats: "Up to 5 team seats",
      features: [
        "1,000,000 rows out-of-core DuckDB engine",
        "10 GB cloud dataset storage",
        "Up to 5 team seats with role permissions",
        "50 AutoML tournaments (LightGBM, XGBoost)",
        "250 AI natural-language queries / mo",
        "Relational Join Studio & multi-table merge",
        "Statistical hypothesis suite (ANOVA, t-test, Chi-Sq)",
        "Priority email support",
      ],
      cta: "Upgrade to Pro",
      popular: false,
    },
    {
      id: "team",
      name: "Team Collaboration",
      badge: "SCALE & GOVERNANCE",
      description: "For analytics engineering teams requiring cloud pushdown and shared governance.",
      price: 79,
      annualPrice: 69,
      limits: "Up to 5,000,000 rows • 50 GB storage",
      seats: "Up to 25 team seats",
      features: [
        "5,000,000 rows out-of-core streaming",
        "50 GB shared organization storage",
        "Up to 25 team seats with 4-tier RBAC",
        "Live Cloud Warehouses (Snowflake, BigQuery, ClickHouse)",
        "200 AutoML tournaments & Model Registry REST API",
        "1-click dbt & Apache Airflow pipeline code export",
        "Immutable governance audit logs & compliance trail",
        "Dedicated engineer support (4h SLA)",
      ],
      cta: "Deploy Team Workspace",
      popular: true,
    },
    {
      id: "enterprise",
      name: "Enterprise Scale",
      badge: "PRIVATE VPC",
      description: "For high-volume enterprises requiring private VPC or zero cloud egress.",
      price: 249,
      annualPrice: 199,
      limits: "20,000,000+ rows • 500 GB storage",
      seats: "Unlimited team seats",
      features: [
        "20M+ rows or unlimited warehouse streaming",
        "500 GB organization storage",
        "Unlimited team seats & SAML 2.0 / Okta SSO",
        "100% Private VPC or on-prem deployment",
        "Customer-Managed Encryption Keys (CMEK)",
        "Dynamic PII scrubbing & column masking",
        "Custom Connector SDKs & 99.99% uptime SLA",
        "24/7 dedicated solutions architect",
      ],
      cta: "Contact Enterprise",
      popular: false,
    },
  ];

  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8 relative border-t border-[var(--border)]">
      <div className="max-w-7xl mx-auto">
        {/* Free Starter subtle banner */}
        <div
          className="mb-10 max-w-2xl mx-auto p-3 sm:p-3.5 rounded-2xl border flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-center sm:text-left shadow-sm"
          style={{ background: "var(--card-bg)", borderColor: "var(--border)" }}
        >
          <div className="flex flex-col sm:flex-row items-center gap-2">
            <span
              className="px-2 py-0.5 rounded text-[10px] font-bold uppercase border shrink-0"
              style={{
                background: "rgba(16, 185, 129, 0.1)",
                borderColor: "rgba(16, 185, 129, 0.3)",
                color: "#10b981",
              }}
            >
              Free Starter
            </span>
            <span style={{ color: "var(--txt-m)" }}>
              Solo analyst? Get started free (up to 100k rows, 500MB storage).
            </span>
          </div>
          <button
            type="button"
            onClick={() => onSelectPlan("free")}
            className="font-bold underline cursor-pointer shrink-0 hover:opacity-80 transition-opacity"
            style={{ color: "var(--accent)" }}
          >
            Launch Free →
          </button>
        </div>

        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider mb-3 border border-[var(--border)] bg-[var(--card-bg)] text-[var(--accent)]">
            <Sparkles size={13} />
            <span>Transparent Public Pricing</span>
          </div>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--txt)] mb-3">
            Predictable plans. Built for data teams.
          </h2>
          <p className="text-sm sm:text-base text-[var(--txt-m)] max-w-xl mx-auto mb-6">
            Keep your costs predictable with out-of-core DuckDB performance.
          </p>

          {/* Billing Cycle Toggle */}
          <div className="inline-flex items-center gap-3 p-1 rounded-full border border-[var(--border)] bg-[var(--card-bg)] shadow-sm">
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

        {/* 3 Paid Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {plans.map((plan) => {
            const currentPrice = billingCycle === "annually" ? plan.annualPrice : plan.price;
            return (
              <motion.div
                key={plan.id}
                whileHover={{ y: -4 }}
                transition={{ duration: 0.2 }}
                className={`relative rounded-3xl p-7 flex flex-col justify-between border transition-all ${
                  plan.popular
                    ? "border-[var(--accent)] bg-[var(--card-bg)] shadow-2xl ring-2 ring-[var(--accent)]/30"
                    : "border-[var(--border)] bg-[var(--card-bg)] shadow-lg"
                }`}
              >
                {/* Popular Pill */}
                {plan.badge && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-[var(--accent)] text-white shadow-md">
                    {plan.badge}
                  </div>
                )}

                <div>
                  <div className="mb-4">
                    <h3 className="text-xl font-bold text-[var(--txt)] mb-1">{plan.name}</h3>
                    <p className="text-xs text-[var(--txt-m)] min-h-[32px]">{plan.description}</p>
                  </div>

                  {/* Price */}
                  <div className="mb-5 pb-5 border-b border-[var(--border)]">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl sm:text-5xl font-black text-[var(--txt)]">
                        ${currentPrice}
                      </span>
                      <span className="text-xs text-[var(--txt-m)] font-semibold">
                        / month
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-[var(--accent)] mt-2">
                      {plan.limits}
                    </div>
                    <div className="text-[11px] font-medium text-[var(--txt-m)] mt-0.5">
                      {plan.seats}
                    </div>
                  </div>

                  {/* Features list */}
                  <div className="space-y-2.5 mb-6">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--txt-m)]">
                      Included Capabilities:
                    </p>
                    {plan.features.map((feat, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-[var(--txt)]">
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
                    onClick={() => onSelectPlan(plan.id)}
                    className={`w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                      plan.popular
                        ? "bg-[var(--accent)] text-white hover:opacity-95 shadow-lg shadow-[var(--accent)]/20"
                        : "bg-[var(--border)] text-[var(--txt)] hover:bg-[var(--accent)] hover:text-white"
                    }`}
                  >
                    <span>{plan.cta}</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Pricing link footer */}
        <div className="mt-10 text-center flex items-center justify-center gap-2 text-xs text-[var(--txt-m)]">
          <span>Looking for detailed specifications and on-prem air-gapped deployment?</span>
          <Link
            href="/pricing"
            className="font-bold text-[var(--accent)] hover:underline flex items-center gap-1"
          >
            <span>View Full Specs</span>
            <ArrowRight size={11} />
          </Link>
        </div>
      </div>
    </section>
  );
}
