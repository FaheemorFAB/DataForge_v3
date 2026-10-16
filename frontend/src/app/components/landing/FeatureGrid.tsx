"use client";

import React, { useEffect, useRef } from "react";
import {
  Wand2,
  LineChart,
  FileSearch,
  Sparkles,
  Bot,
  Cpu,
  ArrowUpRight,
  Database,
  ShieldCheck,
  CheckCircle2,
} from "lucide-react";

export default function FeatureGrid() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1 }
    );

    const items = containerRef.current?.querySelectorAll(".bento-card");
    items?.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  const features = [
    {
      title: "Automated Data Cleaning",
      eyebrow: "STEP 01 / SANITIZE",
      desc: "Instant missing value imputation, duplicate removal, whitespace stripping, and column type coercion with an interactive visual before/after diff.",
      icon: Wand2,
      accent: "var(--accent)",
      tag: "Zero Data Leakage",
      gridSpan: "col-span-1 md:col-span-2 lg:col-span-2",
    },
    {
      title: "Exploratory Profiling (EDA)",
      eyebrow: "STEP 02 / AUDIT",
      desc: "Deep statistical distributions, skewness, quantile spreads, correlation matrices, and anomaly detection computed in parallel across millions of rows.",
      icon: FileSearch,
      accent: "#38bdf8",
      tag: "Realtime Stats",
      gridSpan: "col-span-1 md:col-span-1 lg:col-span-1",
    },
    {
      title: "Generative AI Insights",
      eyebrow: "STEP 03 / REASONING",
      desc: "Automated synthesis translates raw distributions and cross-correlations into executive summaries, key drivers, and actionable strategic takeaways.",
      icon: Sparkles,
      accent: "#a855f7",
      tag: "DataForge AI",
      gridSpan: "col-span-1 md:col-span-1 lg:col-span-1",
    },
    {
      title: "AutoML Engine (FLAML)",
      eyebrow: "STEP 04 / PREDICT",
      desc: "Automatic feature engineering, cross-validation, hyperparameter tuning, and leaderboard generation across LightGBM, XGBoost, and Random Forest.",
      icon: Cpu,
      accent: "#ec4899",
      tag: "Model Leaderboard & .pkl",
      gridSpan: "col-span-1 md:col-span-2 lg:col-span-2",
    },
    {
      title: "Interactive Visualization Hub",
      eyebrow: "STEP 05 / VISUALIZE",
      desc: "Fast responsive charting: scatter plots, violin plots, box plots, histograms, and pinned dashboard widgets with one-click export.",
      icon: LineChart,
      accent: "#6366f1",
      tag: "High-DPI Charts",
      gridSpan: "col-span-1 md:col-span-2 lg:col-span-2",
    },
    {
      title: "Natural Language AI Query",
      eyebrow: "STEP 06 / DIALOGUE",
      desc: "Query your dataset in plain English with context-grounded conversational analytics that automatically runs pandas queries underneath.",
      icon: Bot,
      accent: "#10b981",
      tag: "Chat with Dataset",
      gridSpan: "col-span-1 md:col-span-1 lg:col-span-1",
    },
  ];

  return (
    <section id="features" ref={containerRef} className="py-24 border-t w-full" style={{ borderColor: "var(--border)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-2xl text-left mb-16 space-y-3">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase tracking-wider"
            style={{ background: "rgba(255, 67, 16, 0.08)", color: "var(--accent)" }}>
            Autonomous Engine
          </div>
          <h2 className="text-3xl sm:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
            Six Core Capabilities. <br />
            One Seamless Interface.
          </h2>
          <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
            Replace fragmented notebooks, messy CSV spreadsheets, and clunky BI platforms with an integrated data pipeline designed for speed and clarity.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {features.map((f, i) => {
            const Icon = f.icon;
            return (
              <div
                key={i}
                className={`bento-card ${f.gridSpan} group relative rounded-2xl p-6 sm:p-7 border backdrop-blur-xl transition-all duration-300 hover:border-orange-500/40 hover:-translate-y-1`}
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  boxShadow: "0 10px 30px -10px rgba(0,0,0,0.3)",
                }}
              >
                {/* Subtle Card Ambient Glow */}
                <div
                  className="absolute -top-12 -right-12 w-32 h-32 rounded-full pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-2xl"
                  style={{ background: f.accent }}
                />

                <div className="relative z-10 flex flex-col justify-between h-full space-y-6">
                  {/* Top Header */}
                  <div className="flex items-center justify-between">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center border transition-transform duration-300 group-hover:scale-110"
                      style={{
                        background: "rgba(255, 255, 255, 0.04)",
                        borderColor: "rgba(255, 255, 255, 0.08)",
                        color: f.accent,
                      }}
                    >
                      <Icon size={18} />
                    </div>
                    <span
                      className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold border"
                      style={{
                        background: "rgba(255, 255, 255, 0.02)",
                        borderColor: "var(--border)",
                        color: "var(--txt-m)",
                      }}
                    >
                      {f.tag}
                    </span>
                  </div>

                  {/* Body Content */}
                  <div className="space-y-2">
                    <p className="text-[10px] font-mono font-bold tracking-widest uppercase opacity-60" style={{ color: "var(--txt-m)" }}>
                      {f.eyebrow}
                    </p>
                    <h3 className="text-lg font-bold tracking-tight group-hover:text-white transition-colors" style={{ color: "var(--txt)" }}>
                      {f.title}
                    </h3>
                    <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                      {f.desc}
                    </p>
                  </div>

                  {/* Bottom Indicator */}
                  <div className="pt-2 flex items-center gap-1.5 text-[11px] font-medium opacity-50 group-hover:opacity-100 transition-opacity" style={{ color: f.accent }}>
                    <span>Explore module</span>
                    <ArrowUpRight size={13} className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
