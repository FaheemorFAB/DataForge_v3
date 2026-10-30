"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  GraduationCap,
  Briefcase,
  BookOpen,
  Building2,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export default function BuiltFor() {
  const personas = [
    {
      num: "01",
      role: "Business & Growth Analysts",
      desc: "Instant revenue drivers, KPI cohort breakdowns, and churn metrics without wrestling with complex SQL scripts or python virtualenvs.",
      icon: TrendingUp,
    },
    {
      num: "02",
      role: "Academic & Thesis Researchers",
      desc: "Fast exploratory profiling, variance checks, and baseline AutoML regression/classification models for thesis papers and lab validation.",
      icon: GraduationCap,
    },
    {
      num: "03",
      role: "Product & Growth Managers",
      desc: "User engagement telemetry, feature adoption metrics, and funnel analysis directly from raw event exports.",
      icon: Briefcase,
    },
    {
      num: "04",
      role: "Students & Self-Learners",
      desc: "Grasp end-to-end data science lifecycle—from cleaning to model leadership boards—with a live, transparent pipeline.",
      icon: BookOpen,
    },
    {
      num: "05",
      role: "Founders & SME Leaders",
      desc: "Extract answers from company sales and inventory logs in minutes without hiring a costly dedicated data engineering unit.",
      icon: Building2,
    },
  ];

  const fadeUp = {
    hidden: { opacity: 0, y: 24 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" as const } },
  };

  return (
    <section id="audiences" className="min-h-[100dvh] min-h-[100vh] flex flex-col justify-center py-12 sm:py-16 md:py-20 lg:py-24 border-t w-full transition-colors duration-300" style={{ borderColor: "var(--border)" }}>
      <div className="max-w-6xl mx-auto px-5 sm:px-8 w-full my-auto">
        
        {/* Section Header */}
        <motion.div
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-60px" }}
          variants={fadeUp}
          className="max-w-2xl text-left mb-6 sm:mb-10 lg:mb-14 space-y-2 sm:space-y-3"
        >
          <div className="inline-flex items-center gap-2">
            <span className="text-[11px] font-extrabold font-mono uppercase tracking-widest" style={{ color: "var(--accent)" }}>
              WHO USES DATAFORGE
            </span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-black tracking-tight leading-tight transition-colors duration-300" style={{ color: "var(--txt)" }}>
            Engineered for Anyone Holding a Dataset.
          </h2>
          <p className="text-base sm:text-lg leading-relaxed transition-colors duration-300" style={{ color: "var(--txt-m)" }}>
            No python environments to configure. No SQL databases to tune. Instant answers from the moment you drop a file.
          </p>
        </motion.div>

        {/* Rows */}
        <div className="space-y-2.5 sm:space-y-3.5">
          {personas.map((p, idx) => {
            const Icon = p.icon;
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ delay: idx * 0.08, duration: 0.4 }}
                className="audience-row group flex items-start sm:items-center justify-between p-3 sm:p-5 md:p-6 rounded-2xl border transition-all duration-300 hover:border-[var(--accent)] hover:-translate-y-0.5 hover:shadow-xl relative overflow-hidden"
                style={{
                  borderColor: "var(--border)",
                  background: "var(--card-bg, var(--card))",
                }}
              >
                {/* Subtle hover accent sheen */}
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
                  style={{
                    background: "radial-gradient(circle at left center, rgba(255, 67, 16, 0.03), transparent 70%)",
                  }}
                />

                <div className="flex items-start sm:items-center gap-3.5 sm:gap-5 flex-1 min-w-0 relative z-10">
                  <div
                    className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl flex items-center justify-center flex-shrink-0 border transition-transform duration-300 group-hover:scale-105"
                    style={{
                      background: "rgba(255, 67, 16, 0.08)",
                      borderColor: "rgba(255, 67, 16, 0.25)",
                      color: "var(--accent)",
                    }}
                  >
                    <Icon size={18} className="sm:w-5 sm:h-5" />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-12 gap-1 md:gap-5 flex-1 items-start sm:items-center">
                    <span className="text-sm sm:text-base font-bold md:col-span-4 group-hover:text-[var(--accent)] transition-colors" style={{ color: "var(--txt)" }}>
                      {p.role}
                    </span>
                    <span className="text-xs sm:text-sm md:col-span-8 leading-relaxed" style={{ color: "var(--txt-m)" }}>
                      {p.desc}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 sm:gap-3 pl-2 sm:pl-4 flex-shrink-0 relative z-10">
                  <span className="text-xs font-mono font-bold opacity-40 group-hover:opacity-100 group-hover:text-[var(--accent)] transition-all" style={{ color: "var(--txt-m)" }}>
                    {p.num}
                  </span>
                  <ArrowRight size={15} className="opacity-0 group-hover:opacity-100 transition-all -translate-x-1 group-hover:translate-x-0 hidden sm:block" style={{ color: "var(--accent)" }} />
                </div>
              </motion.div>
            );
          })}
        </div>

      </div>
    </section>
  );
}
