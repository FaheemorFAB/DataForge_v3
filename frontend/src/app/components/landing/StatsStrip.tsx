"use client";

import React, { useEffect, useRef } from "react";
import { Sparkles, TrendingUp, Zap, CheckCircle2 } from "lucide-react";

export default function StatsStrip() {
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
      { threshold: 0.15 }
    );

    const el = containerRef.current;
    if (el) observer.observe(el);

    return () => observer.disconnect();
  }, []);

  const stats = [
    {
      num: "4.2M+",
      label: "Rows Processed",
      desc: "Zero-latency batch ingestion & sanitization",
      icon: Zap,
    },
    {
      num: "96.4%",
      label: "Avg. Quality Boost",
      desc: "Post-imputation completeness score",
      icon: CheckCircle2,
    },
    {
      num: "< 2.8s",
      label: "Time to First Insight",
      desc: "From file drop to visual distribution metrics",
      icon: TrendingUp,
    },
    {
      num: "0",
      label: "Lines of Code Required",
      desc: "Completely autonomous point-and-click workflow",
      icon: Sparkles,
    },
  ];

  return (
    <section
      ref={containerRef}
      className="py-14 border-t border-b w-full transition-colors duration-300"
      style={{
        borderColor: "var(--border)",
        background: "var(--surface)",
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          {stats.map((s, idx) => {
            const Icon = s.icon;
            return (
              <div
                key={idx}
                className="flex flex-col text-left space-y-2 relative p-4 rounded-xl transition-all duration-300 hover:bg-white/[0.02]"
              >
                <div className="flex items-center gap-2">
                  <Icon size={14} style={{ color: "var(--accent)" }} />
                  <span className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>
                    {s.label}
                  </span>
                </div>
                <div
                  className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight"
                  style={{
                    color: "var(--txt)",
                  }}
                >
                  {s.num}
                </div>
                <p className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
                  {s.desc}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
