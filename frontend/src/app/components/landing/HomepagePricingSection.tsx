"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Check, X, Sparkles, ArrowRight } from "lucide-react";

interface Props {
  onSelectPlan: (plan: string) => void;
}

export default function HomepagePricingSection({ onSelectPlan }: Props) {
  // Exactly 2 Paid Tiers (Pro Analyst & Team Collaboration)
  const plans = [
    {
      id: "pro",
      name: "Pro Analyst",
      badge: "MOST POPULAR",
      description: "For solo data analysts requiring full export formats, EDA presentation slides & AutoML Docker containers.",
      price: 29,
      limits: "Up to 250,000 rows • 5 GB storage",
      seats: "1 solo practitioner seat",
      features: [
        "Unlimited Data Ingestion (no file count or monthly ingest caps)",
        "250,000 rows in-memory DuckDB processing (10x Free)",
        "Data Ingestion: Local CSV/Excel, Google Sheets & OneDrive/M365",
        "Full File Downloads: CSV, Excel, Parquet & JSON",
        "Executive EDA presentation slides export (PPTX & PDF)",
        "AutoML production Docker containers & deployment files",
        "Pipeline Code Export: Standalone Python & dbt models",
        "50 AutoML tournaments (LightGBM, XGBoost)",
        "250 AI natural-language queries / mo (10x Free)",
        "Relational Join Studio & multi-table merge",
        "Priority email support",
      ],
      nonFeatures: [
        "Shared Database Connection Vault (PostgreSQL, MySQL, SQLite, DuckDB)",
        "Apache Airflow production DAG exports & database push",
        "Multi-user team collaboration & 3-tier roles",
      ],
      cta: "Upgrade to Pro Analyst",
      popular: false,
    },
    {
      id: "team",
      name: "Team Collaboration",
      badge: "SCALE & GOVERNANCE",
      description: "For analytics teams requiring shared datasets, collaboration with 3 roles and database connections.",
      price: 79,
      limits: "Up to 1,000,000 rows • 25 GB storage",
      seats: "Up to 5 seats (Viewer, Analyst, Admin)",
      features: [
        "Multi-user team collaboration with 3 roles: Viewer, Analyst, Admin",
        "Up to 5 seats with granular permission roles",
        "Shared Database Connection Vault (PostgreSQL, MySQL, SQLite, DuckDB)",
        "1,000,000 rows out-of-core streaming (4x Pro, 40x Free)",
        "25 GB shared organization storage (5x Pro)",
        "Unlimited Team Data Ingestion & Pipeline Uploads",
        "Apache Airflow production DAG exports & pipeline code",
        "Direct Database Push & Cross-team exports",
        "200 AutoML tournaments & Model Registry REST API (4x Pro)",
        "1,000 AI natural-language queries / mo (4x Pro)",
        "Immutable governance audit logs & compliance trail",
      ],
      nonFeatures: [],
      cta: "Deploy Team Workspace",
      popular: true,
    },
  ];

  return (
    <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8 relative border-t border-[var(--border)]">
      <div className="max-w-7xl mx-auto">


        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-12">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[var(--txt)] mb-3">
            Predictable plans. Built for data teams.
          </h2>
          <p className="text-sm sm:text-base text-[var(--txt-m)] max-w-xl mx-auto mb-6">
            Keep your costs predictable with out-of-core DuckDB performance.
          </p>
        </div>

        {/* Paid Pricing Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8 items-stretch max-w-4xl mx-auto">
          {plans.map((plan) => {
            const currentPrice = plan.price;
            return (
              <motion.div
                key={plan.id}
                whileHover={{ y: -4 }}
                transition={{ duration: 0.2 }}
                className={`relative rounded-3xl p-5 sm:p-6 lg:p-7 flex flex-col justify-between border transition-all ${plan.popular
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
                    {plan.id === "pro" && (
                      <div
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold mb-3 shadow-sm"
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
                    {plan.id === "team" && (
                      <div
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold mb-3 shadow-sm"
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
                    <p className="text-[10px] font-bold uppercase tracking-wider text-[var(--txt-m)]">
                      Exclusive Capabilities:
                    </p>
                    {plan.features.map((feat, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs text-[var(--txt)]">
                        <div className="w-4 h-4 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5 border border-emerald-500/30">
                          <Check size={10} strokeWidth={3} />
                        </div>
                        <span className="leading-tight">{feat}</span>
                      </div>
                    ))}

                    {plan.nonFeatures && plan.nonFeatures.length > 0 && (
                      <div className="pt-2.5 border-t border-[var(--border)]/50 space-y-2.5">
                        {plan.nonFeatures.map((feat, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs opacity-50 text-[var(--txt-m)]">
                            <div className="w-4 h-4 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center shrink-0 mt-0.5 border border-red-500/25">
                              <X size={10} strokeWidth={2.5} />
                            </div>
                            <span className="leading-tight">{feat}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* CTA Button */}
                <div>
                  <button
                    type="button"
                    onClick={() => onSelectPlan(plan.id)}
                    className={`w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${plan.popular
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
