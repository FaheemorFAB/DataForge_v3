"use client";

import React, { useRef, useState } from "react";
import { motion, useScroll, useTransform, useMotionValueEvent } from "framer-motion";
import {
  UploadCloud,
  Wand2,
  BarChart3,
  Bot,
  Cpu,
  FileCheck2,
} from "lucide-react";

const STEPS = [
  { title: "Ingest", desc: "CSV, Sheets, or SQL", num: "01", icon: UploadCloud },
  { title: "Clean", desc: "Auto null-impute & sanitize", num: "02", icon: Wand2 },
  { title: "Profile", desc: "Distributions & correlations", num: "03", icon: BarChart3 },
  { title: "Ask AI", desc: "Conversational synthesis", num: "04", icon: Bot },
  { title: "Model", desc: "FLAML AutoML tuning", num: "05", icon: Cpu },
  { title: "Report", desc: "Export & production metrics", num: "06", icon: FileCheck2 },
];

export default function ProcessTimeline() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 85%", "end 45%"],
  });

  const widthProgress = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);
  const heightProgress = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  useMotionValueEvent(scrollYProgress, "change", (latest) => {
    const index = Math.min(5, Math.floor(latest * 5.99));
    setActiveIndex(index);
  });

  return (
    <section id="process" className="py-24 w-full border-t" style={{ borderColor: "var(--border)" }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Section Header */}
        <div className="max-w-xl text-left mb-16 space-y-2">
          <p className="text-[10px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
            PIPELINE ARCHITECTURE
          </p>
          <h2 className="text-3xl sm:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
            From Ingestion to Model in Seconds.
          </h2>
          <p className="text-sm leading-relaxed" style={{ color: "var(--txt-m)" }}>
            Every dataset follows a validated autonomous sequence, ensuring zero data leakage and production-grade validation.
          </p>
        </div>

        {/* Timeline Line & Steps */}
        <div ref={containerRef} className="relative flex flex-col md:flex-row items-center justify-between w-full px-2 gap-y-12 md:gap-y-0">
          
          {/* Background rail */}
          <div
            className="absolute top-0 md:top-[28px] left-1/2 md:left-0 -translate-x-1/2 md:translate-x-0 w-[2px] md:w-full h-full md:h-[3px] rounded-full"
            style={{ background: "var(--border)", zIndex: 0 }}
          />

          {/* Active Animated Progress Line (Mobile) */}
          <motion.div
            className="md:hidden absolute top-0 left-1/2 -translate-x-1/2 w-[2px] rounded-full"
            style={{
              zIndex: 1,
              background: "var(--accent)",
              boxShadow: "0 0 12px var(--glow)",
              height: heightProgress,
            }}
          />

          {/* Active Animated Progress Line (Desktop) */}
          <motion.div
            className="hidden md:block absolute top-[28px] left-0 h-[3px] rounded-full"
            style={{
              zIndex: 1,
              background: "var(--accent)",
              boxShadow: "0 0 12px var(--glow)",
              width: widthProgress,
            }}
          />

          {STEPS.map((step, i) => {
            const isDone = i < activeIndex;
            const isActive = i === activeIndex;
            const Icon = step.icon;

            const borderColor = isDone || isActive ? "var(--accent)" : "var(--border)";
            const outerBg = isDone || isActive ? "var(--bg)" : "var(--surface)";
            const shadow = isDone || isActive ? "0 0 16px var(--glow)" : "none";
            const iconColor = isDone || isActive ? "var(--accent)" : "var(--txt-m)";

            return (
              <div
                key={i}
                className="relative z-10 flex flex-col items-center group cursor-default transition-all duration-300 w-full md:w-auto"
              >
                <div className="relative flex-shrink-0">
                  {isActive && (
                    <div
                      className="absolute inset-0 rounded-full border-2 animate-ping opacity-25"
                      style={{ borderColor: "var(--accent)" }}
                    />
                  )}
                  <div
                    className="w-14 h-14 rounded-full border-2 flex items-center justify-center transition-all duration-300 group-hover:scale-105 shadow-sm"
                    style={{ borderColor, background: outerBg, boxShadow: shadow }}
                  >
                    <Icon size={20} style={{ color: iconColor }} className="transition-transform group-hover:scale-110" />
                  </div>
                </div>

                <div className="mt-4 md:mt-0 md:absolute md:top-20 min-w-max text-center transition-all duration-300">
                  <p className="text-[10px] font-mono font-bold tracking-widest uppercase opacity-60" style={{ color: "var(--txt-m)" }}>
                    {step.num}
                  </p>
                  <p className="text-sm font-bold tracking-tight mt-0.5" style={{ color: isDone || isActive ? "var(--txt)" : "var(--txt-m)" }}>
                    {step.title}
                  </p>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>
                    {step.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="hidden md:block h-24 w-full"></div>
      </div>
    </section>
  );
}
