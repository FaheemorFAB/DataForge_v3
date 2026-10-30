"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, useInView, AnimatePresence } from "framer-motion";
import Header from "./components/landing/Header";
import Footer from "./components/landing/Footer";
import LoginModal from "./components/landing/LoginModal";
import SplashLoader from "./components/SplashLoader";
import BuiltFor from "./components/landing/BuiltFor";
import TeamSection from "./components/landing/TeamSection";
import CTABanner from "./components/landing/CTABanner";
import Scratch from "./components/ui/Scratch";
import WorkspaceLaunchModal from "./components/landing/WorkspaceLaunchModal";
import ThreeHeroVisual from "./components/landing/ThreeHeroVisual";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

import {
  UploadCloud,
  Wand2,
  Activity,
  MessageSquareCode,
  Cpu,
  FileText,
  Globe,
  Server,
  Bot,
  Key,
  HardDrive,
  Zap,
  ArrowRight,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  X,
  FileSpreadsheet,
  Table as TableIcon,
  Database,
  RefreshCw,
  Sparkles,
} from "lucide-react";

/* ─── Animated counter ───────────────────────────────────────────────────── */
function Counter({ to, suffix = "" }: { to: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const [count, setCount] = useState(0);

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const step = Math.ceil(to / 60);
    const timer = setInterval(() => {
      start += step;
      if (start >= to) {
        setCount(to);
        clearInterval(timer);
      } else {
        setCount(start);
      }
    }, 16);
    return () => clearInterval(timer);
  }, [inView, to]);

  return (
    <span ref={ref}>
      {count}
      {suffix}
    </span>
  );
}

/* ─── Tiny spark bar ─────────────────────────────────────────────────────── */
function SparkBar({ heights }: { heights: number[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  return (
    <div ref={ref} className="flex items-end gap-0.5 h-8">
      {heights.map((h, i) => (
        <motion.div
          key={i}
          initial={{ scaleY: 0 }}
          animate={inView ? { scaleY: 1 } : { scaleY: 0 }}
          transition={{ delay: i * 0.05, duration: 0.4, ease: "easeOut" }}
          style={{
            originY: 1,
            height: `${h}%`,
            background: "var(--accent)",
            opacity: 0.5 + h / 250,
          }}
          className="w-1.5 rounded-sm flex-shrink-0"
        />
      ))}
    </div>
  );
}

/* ─── Stage visual panels ────────────────────────────────────────────────── */
function IngestVisual() {
  const rows = [
    ["customer_id", "age", "income", "churn"],
    ["C001", "34", "72000", "null"],
    ["C002", "null", "null", "1"],
    ["C003", "28", "55000", "0"],
    ["C004", "null", "88000", "1"],
    ["C005", "41", "null", "0"],
  ];
  return (
    <div className="w-full flex flex-col gap-3">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
        <span
          className="text-[10px] font-bold uppercase tracking-widest"
          style={{ color: "var(--txt-m)" }}
        >
          customer_data.csv · 5,000 rows detected
        </span>
      </div>
      <div
        className="overflow-x-auto rounded-xl border"
        style={{ borderColor: "var(--border)" }}
      >
        <table className="w-full text-xs">
          <thead>
            <tr style={{ background: "var(--bg)" }}>
              {rows[0].map((h, i) => (
                <th
                  key={i}
                  className="px-3 py-2 text-left font-bold"
                  style={{
                    color: "var(--accent)",
                    borderBottom: "1px solid var(--border)",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(1).map((row, ri) => (
              <motion.tr
                key={ri}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: ri * 0.12 }}
                style={{
                  background: ri % 2 === 0 ? "var(--card-bg)" : "transparent",
                }}
              >
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className="px-3 py-1.5 font-mono"
                    style={{
                      color: cell === "null" ? "#EF4444" : "var(--txt)",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    {cell === "null" ? (
                      <span className="italic opacity-70">null</span>
                    ) : (
                      cell
                    )}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex gap-2 mt-1">
        {["CSV", "Excel", "Sheets"].map((f) => (
          <span
            key={f}
            className="text-[10px] font-bold px-2.5 py-1 rounded-full border"
            style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
          >
            {f}
          </span>
        ))}
        <span
          className="text-[10px] font-bold px-2.5 py-1 rounded-full ml-auto"
          style={{ background: "var(--accent)", color: "#fff" }}
        >
          Parsed ✓
        </span>
      </div>
    </div>
  );
}

function CleanVisual() {
  const bars = [
    { label: "Missing Values", before: 18, after: 0, color: "#EF4444" },
    { label: "Duplicates", before: 7, after: 0, color: "#F97316" },
    { label: "Outliers (Z>3)", before: 4, after: 0, color: "#EAB308" },
    { label: "Type Errors", before: 9, after: 0, color: "#A855F7" },
  ];
  return (
    <div className="flex flex-col gap-4 w-full">
      <div
        className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider mb-1"
        style={{ color: "var(--txt-m)" }}
      >
        <span>Issue</span>
        <span className="flex gap-6">
          <span style={{ color: "#EF4444" }}>Before</span>
          <span style={{ color: "#22c55e" }}>After</span>
        </span>
      </div>
      {bars.map((b, i) => (
        <div key={i} className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span
              className="text-xs font-semibold"
              style={{ color: "var(--txt)" }}
            >
              {b.label}
            </span>
            <div className="flex gap-4 text-xs font-bold">
              <span style={{ color: b.color }}>{b.before}%</span>
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.2 + 0.5 }}
                style={{ color: "#22c55e" }}
              >
                0%
              </motion.span>
            </div>
          </div>
          <div
            className="relative h-2 rounded-full overflow-hidden"
            style={{ background: "var(--border)" }}
          >
            <div
              className="absolute inset-0 rounded-full"
              style={{ background: b.color, opacity: 0.25 }}
            />
            <motion.div
              className="absolute left-0 top-0 h-full rounded-full"
              initial={{ width: `${b.before}%` }}
              animate={{ width: "0%" }}
              transition={{
                delay: i * 0.2 + 0.3,
                duration: 0.8,
                ease: "easeInOut",
              }}
              style={{ background: b.color }}
            />
          </div>
        </div>
      ))}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.2 }}
        className="flex items-center gap-2 mt-2 px-4 py-2.5 rounded-xl"
        style={{ background: "#22c55e18", border: "1px solid #22c55e40" }}
      >
        <CheckCircle2 size={16} style={{ color: "#22c55e" }} />
        <span className="text-xs font-bold" style={{ color: "#22c55e" }}>
          Dataset sanitized · 0 issues remaining
        </span>
      </motion.div>
    </div>
  );
}

function AnalyzeVisual() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  return (
    <div ref={ref} className="flex flex-col gap-4 w-full">
      <div className="flex items-center gap-3 mb-1">
        <span
          className="text-[10px] font-bold uppercase tracking-wider"
          style={{ color: "var(--txt-m)" }}
        >
          Monthly Revenue Trend
        </span>
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-full ml-auto"
          style={{ background: "#3B82F618", color: "#3B82F6" }}
        >
          +14.2% trend
        </span>
      </div>
      {/* Line chart area */}
      <div className="relative h-32 w-full">
        <svg
          viewBox="0 0 300 80"
          className="w-full h-full"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="analyzeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
            </linearGradient>
          </defs>
          <motion.path
            d="M0,60 C25,55 50,45 75,40 S125,30 150,25 S200,18 225,14 S275,8 300,5"
            fill="none"
            stroke="#3B82F6"
            strokeWidth="2"
            strokeLinecap="round"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={inView ? { pathLength: 1, opacity: 1 } : {}}
            transition={{ duration: 1.2, ease: "easeInOut" }}
          />
          <motion.path
            d="M0,60 C25,55 50,45 75,40 S125,30 150,25 S200,18 225,14 S275,8 300,5 L300,80 L0,80 Z"
            fill="url(#analyzeGrad)"
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ delay: 0.8, duration: 0.6 }}
          />
        </svg>
      </div>
      {/* Insight chips */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: "Pearson r = 0.87", sub: "Income → Churn", color: "#6366F1" },
          { label: "Anomaly at row 42", sub: "Z-score: 3.8", color: "#EF4444" },
          { label: "Peak: Q3 2024", sub: "Category insight", color: "#F59E0B" },
          { label: "14 plugins ran", sub: "0 errors", color: "#22c55e" },
        ].map((chip, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.6 + i * 0.15 }}
            className="px-3 py-2 rounded-xl border flex flex-col gap-0.5"
            style={{
              borderColor: chip.color + "40",
              background: chip.color + "0D",
            }}
          >
            <span
              className="text-[11px] font-bold"
              style={{ color: chip.color }}
            >
              {chip.label}
            </span>
            <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>
              {chip.sub}
            </span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function AIVisual() {
  const messages = [
    { role: "user", text: "What's the top factor driving customer churn?" },
    {
      role: "ai",
      text: "Based on your dataset, low income (<$40K) combined with age under 30 predicts churn with 89% accuracy. These 312 customers are your highest-risk segment.",
    },
  ];
  return (
    <div className="flex flex-col gap-3 w-full">
      <div className="flex items-center gap-2 mb-1">
        <Bot size={14} style={{ color: "#6366F1" }} />
        <span
          className="text-[10px] font-bold uppercase tracking-wider"
          style={{ color: "var(--txt-m)" }}
        >
          DataForge AI · Instant Chat
        </span>
        <div className="ml-auto flex gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>
            Live
          </span>
        </div>
      </div>
      {messages.map((m, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.6 }}
          className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-xs leading-relaxed`}
            style={
              m.role === "user"
                ? {
                  background: "#6366F1",
                  color: "#fff",
                  borderBottomRightRadius: "4px",
                }
                : {
                  background: "var(--card-bg)",
                  border: "1px solid var(--border)",
                  color: "var(--txt)",
                  borderBottomLeftRadius: "4px",
                }
            }
          >
            {m.text}
          </div>
        </motion.div>
      ))}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4 }}
        className="flex items-center gap-2 px-3 py-2 rounded-xl border mt-1"
        style={{ borderColor: "var(--border)", background: "var(--card-bg)" }}
      >
        <span className="text-xs flex-1" style={{ color: "var(--txt-m)" }}>
          Ask anything about your data…
        </span>
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center"
          style={{ background: "#6366F1" }}
        >
          <ArrowRight size={10} color="#fff" />
        </div>
      </motion.div>
    </div>
  );
}

function PredictVisual() {
  const shapBars = [
    { feature: "income", imp: 82, color: "#A855F7" },
    { feature: "age", imp: 65, color: "#A855F7" },
    { feature: "tenure_months", imp: 54, color: "#A855F7" },
    { feature: "num_products", imp: 37, color: "#A855F7" },
    { feature: "is_active", imp: 28, color: "#A855F7" },
  ];
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true });
  return (
    <div ref={ref} className="flex flex-col gap-4 w-full">
      <div className="flex gap-3">
        {[
          { label: "Best Model", val: "XGBoost" },
          { label: "Accuracy", val: "91.4%" },
          { label: "RMSE", val: "0.083" },
        ].map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ delay: i * 0.15 }}
            className="flex-1 px-3 py-2 rounded-xl border flex flex-col gap-0.5 text-center"
            style={{ background: "#A855F70D", borderColor: "#A855F740" }}
          >
            <span className="text-base font-black" style={{ color: "#A855F7" }}>
              {s.val}
            </span>
            <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>
              {s.label}
            </span>
          </motion.div>
        ))}
      </div>
      <div className="flex flex-col gap-2.5">
        <span
          className="text-[10px] font-bold uppercase tracking-wider"
          style={{ color: "var(--txt-m)" }}
        >
          SHAP Feature Importance
        </span>
        {shapBars.map((b, i) => (
          <div key={i} className="flex items-center gap-3">
            <span
              className="text-[11px] font-mono w-28 shrink-0"
              style={{ color: "var(--txt)" }}
            >
              {b.feature}
            </span>
            <div
              className="flex-1 h-2 rounded-full overflow-hidden"
              style={{ background: "var(--border)" }}
            >
              <motion.div
                className="h-full rounded-full"
                style={{ background: b.color }}
                initial={{ width: 0 }}
                animate={inView ? { width: `${b.imp}%` } : {}}
                transition={{
                  delay: i * 0.12 + 0.3,
                  duration: 0.6,
                  ease: "easeOut",
                }}
              />
            </div>
            <span
              className="text-[11px] font-bold w-7 text-right"
              style={{ color: b.color }}
            >
              {b.imp}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReportVisual() {
  const pieData = [
    { label: "Churned", pct: 38, color: "#EF4444" },
    { label: "At-risk", pct: 24, color: "#F59E0B" },
    { label: "Retained", pct: 38, color: "#22c55e" },
  ];
  return (
    <div className="flex flex-col gap-4 w-full">
      <div className="flex gap-4 items-center">
        {/* mini donut */}
        <div className="relative w-24 h-24 shrink-0">
          <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
            {(() => {
              let offset = 0;
              return pieData.map((s, i) => {
                const dash = (s.pct / 100) * 88;
                const el = (
                  <motion.circle
                    key={i}
                    cx="18"
                    cy="18"
                    r="14"
                    fill="none"
                    stroke={s.color}
                    strokeWidth="7"
                    strokeDasharray={`${dash} 88`}
                    strokeDashoffset={-offset}
                    initial={{ strokeDasharray: "0 88" }}
                    animate={{ strokeDasharray: `${dash} 88` }}
                    transition={{ delay: i * 0.3, duration: 0.6 }}
                  />
                );
                offset += dash;
                return el;
              });
            })()}
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span
              className="text-xs font-black"
              style={{ color: "var(--txt)" }}
            >
              5K
            </span>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          {pieData.map((s) => (
            <div key={s.label} className="flex items-center gap-2">
              <div
                className="w-2.5 h-2.5 rounded-sm"
                style={{ background: s.color }}
              />
              <span className="text-xs" style={{ color: "var(--txt)" }}>
                {s.label}
              </span>
              <span
                className="text-xs font-bold ml-auto"
                style={{ color: s.color }}
              >
                {s.pct}%
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="flex gap-2 flex-wrap">
        {[
          "Executive PDF",
          "EDA Profile",
          "Chart.js Dashboard",
          "CSV Export",
        ].map((tag) => (
          <span
            key={tag}
            className="text-[10px] font-bold px-2.5 py-1 rounded-full border"
            style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
          >
            {tag}
          </span>
        ))}
      </div>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1 }}
        className="flex items-center gap-2 px-4 py-2.5 rounded-xl"
        style={{ background: "#F59E0B18", border: "1px solid #F59E0B40" }}
      >
        <TrendingUp size={14} style={{ color: "#F59E0B" }} />
        <span className="text-xs font-bold" style={{ color: "#F59E0B" }}>
          Report generated in 2.3 seconds
        </span>
      </motion.div>
    </div>
  );
}

/* ─── Pipeline data with visual component ────────────────────────────────── */
const PIPELINE_STAGES = [
  {
    num: "01",
    label: "Ingest",
    icon: UploadCloud,
    color: "#FF5722",
    desc: "Upload CSV, Excel or Google Sheets. DataForge auto-detects delimiters, data types and schema in seconds.",
    Visual: IngestVisual,
  },
  {
    num: "02",
    label: "Clean",
    icon: Wand2,
    color: "#EF4444",
    desc: "Impute missing values, remove duplicates and eliminate Z-score outliers automatically. Zero manual steps.",
    Visual: CleanVisual,
  },
  {
    num: "03",
    label: "Analyze",
    icon: Activity,
    color: "#3B82F6",
    desc: "14 deterministic plugins surface trends, Pearson correlations, anomaly spikes and forecasts.",
    Visual: AnalyzeVisual,
  },
  {
    num: "04",
    label: "Ask AI",
    icon: MessageSquareCode,
    color: "#6366F1",
    desc: "Query your dataset in plain English. The DataForge AI engine returns instant, data-backed answers.",
    Visual: AIVisual,
  },
  {
    num: "05",
    label: "Predict",
    icon: Cpu,
    color: "#A855F7",
    desc: "FLAML auto-selects and tunes the best ML model. SHAP charts explain every prediction.",
    Visual: PredictVisual,
  },
  {
    num: "06",
    label: "Report",
    icon: FileText,
    color: "#F59E0B",
    desc: "Interactive Chart.js dashboards, ydata EDA profiles and one-click executive PDF exports.",
    Visual: ReportVisual,
  },
];

function getStageGradientEnd(color: string): string {
  switch (color.toUpperCase()) {
    case "#FF5722":
      return "#FF8A65";
    case "#EF4444":
      return "#F43F5E";
    case "#3B82F6":
      return "#06B6D4";
    case "#6366F1":
      return "#8B5CF6";
    case "#A855F7":
      return "#EC4899";
    case "#F59E0B":
      return "#EA580C";
    default:
      return color;
  }
}

/* ─── Pipeline showcase — interactive sticky section ─────────────────────── */
function PipelineShowcase({ onTryDataset }: { onTryDataset: () => void }) {
  const [active, setActive] = useState(0);
  const outerRef = useRef<HTMLDivElement>(null);
  const visualPanelRef = useRef<HTMLDivElement>(null);
  const { Visual, color } = PIPELINE_STAGES[active];
  const [isPaused, setIsPaused] = useState(false);
  const pauseTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleStageSelect = (index: number) => {
    setActive(index);
    setIsPaused(true);
    if (pauseTimerRef.current) clearTimeout(pauseTimerRef.current);
    pauseTimerRef.current = setTimeout(() => {
      setIsPaused(false);
    }, 7000);
  };

  useEffect(() => {
    const onScroll = () => {
      if (typeof window !== "undefined" && (window as any).__isProgrammaticScrolling) {
        return;
      }
      const outer = outerRef.current;
      if (!outer) return;
      const rect = outer.getBoundingClientRect();
      const scrollable = outer.offsetHeight - window.innerHeight;
      if (scrollable <= 0) return;
      const scrolled = Math.max(0, -rect.top);
      const progress = scrollable > 0 ? Math.min(1, scrolled / scrollable) : 0;
      const idx = Math.min(
        PIPELINE_STAGES.length - 1,
        Math.floor(progress * PIPELINE_STAGES.length)
      );
      setActive((prev) => (prev !== idx ? idx : prev));
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const timelineFill = (active / (PIPELINE_STAGES.length - 1)) * 100;

  return (
    <div ref={outerRef} className="relative h-[240vh] md:h-[400vh] lg:h-[600vh]">
      <div className="sticky top-16 h-[calc(100dvh-64px)] h-[calc(100vh-64px)] flex flex-col justify-center overflow-hidden px-5 sm:px-8 py-4 lg:py-0">
        <div className="max-w-6xl mx-auto w-full flex flex-col gap-8">
          {/* Section header */}
          <div className="flex flex-col gap-2">
            <span
              className="text-[11px] font-extrabold uppercase tracking-widest"
              style={{ color: "var(--accent)" }}
            >
              How It Works
            </span>
            <h2
              className="text-3xl sm:text-5xl font-black tracking-tight"
              style={{ color: "var(--txt)" }}
            >
              6-Stage Automated Pipeline
            </h2>
          </div>

          {/* Split — Visual animation hidden on mobile screens */}
          <div className="flex flex-col md:flex-row gap-6 md:gap-8 lg:gap-12 items-start">
            {/* Left (on desktop) / Full width (on mobile) — timeline of 6 pipelines */}
            <div className="w-full md:w-5/12 lg:w-2/5 relative flex flex-col gap-0 order-1">
              <div
                className="absolute left-6 top-0 bottom-0 w-px"
                style={{ background: "var(--border)", zIndex: 0 }}
              />
              <div
                className="absolute left-6 top-0 w-px transition-all duration-500 ease-out"
                style={{
                  height: `${timelineFill}%`,
                  background: `linear-gradient(to bottom, ${PIPELINE_STAGES[0].color}, ${PIPELINE_STAGES[active].color})`,
                  zIndex: 0,
                }}
              />

              {PIPELINE_STAGES.map((step, i) => {
                const isActive = active === i;
                const isPast = i < active;
                return (
                  <button
                    key={i}
                    onClick={() => handleStageSelect(i)}
                    className="relative z-10 pl-16 pb-3.5 sm:pb-5 last:pb-0 text-left group w-full cursor-pointer"
                  >
                    <div
                      className="absolute left-0 top-0 w-12 h-12 rounded-full z-10"
                      style={{ background: "var(--bg)" }}
                    >
                      <div
                        className="w-full h-full rounded-full flex items-center justify-center border-2 transition-all duration-300"
                        style={{
                          borderColor:
                            isActive || isPast ? step.color : "var(--border)",
                          background: isActive
                            ? step.color + "22"
                            : isPast
                              ? step.color + "10"
                              : "var(--card-bg)",
                          boxShadow: isActive
                            ? `0 0 20px ${step.color}55`
                            : "none",
                        }}
                      >
                        <step.icon
                          size={18}
                          style={{
                            color:
                              isActive || isPast ? step.color : "var(--txt-m)",
                          }}
                        />
                      </div>
                    </div>
                    <div className="flex flex-col gap-0.5 pt-2">
                      <span
                        className="text-[10px] font-black uppercase tracking-wider"
                        style={{
                          color: isActive
                            ? step.color
                            : isPast
                              ? step.color + "88"
                              : "var(--txt-m)",
                        }}
                      >
                        Stage {step.num}
                      </span>
                      <h3
                        className="text-base font-extrabold transition-colors duration-200"
                        style={{
                          color: isActive ? "var(--txt)" : "var(--txt-m)",
                          opacity: isPast ? 0.6 : 1,
                        }}
                      >
                        {step.label}
                      </h3>
                      <AnimatePresence>
                        {isActive && (
                          <motion.p
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="text-sm leading-relaxed mt-1 overflow-hidden"
                            style={{ color: "var(--txt-m)" }}
                          >
                            {step.desc}
                          </motion.p>
                        )}
                      </AnimatePresence>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Right (on desktop) — visual animation panel (hidden on mobile screens) */}
            <div ref={visualPanelRef} className="hidden md:block w-full md:w-7/12 lg:w-3/5 order-2">
              <div
                className="rounded-2xl border overflow-hidden shadow-2xl transition-all duration-500"
                style={{
                  borderColor: color + "50",
                  background: "var(--card-bg)",
                  boxShadow: `0 8px 40px ${color}18`,
                }}
              >
                {/* browser chrome */}
                <div
                  className="flex items-center gap-2 px-4 py-3 border-b"
                  style={{
                    borderColor: "var(--border)",
                    background: "var(--bg)",
                  }}
                >
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500" />
                  <div
                    className="flex-1 mx-3 h-6 rounded-md px-3 flex items-center text-[10px] font-mono"
                    style={{
                      background: "var(--card-bg)",
                      color: "var(--txt-m)",
                    }}
                  >
                    dataforge.app / workspace
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div
                      className="w-2 h-2 rounded-full animate-pulse"
                      style={{ background: color }}
                    />
                    <span
                      className="text-[10px] font-bold"
                      style={{ color }}
                    >
                      {PIPELINE_STAGES[active].label}
                    </span>
                  </div>
                </div>

                {/* visual content */}
                <div className="p-3.5 sm:p-6">
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={active}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -12 }}
                      transition={{ duration: 0.3, ease: "easeInOut" }}
                    >
                      <Visual />
                    </motion.div>
                  </AnimatePresence>
                </div>

                {/* CTA strip */}
                <div className="px-3.5 sm:px-6 pb-3.5 sm:pb-5">
                  <button
                    onClick={onTryDataset}
                    className="relative overflow-hidden flex items-center justify-between w-full px-5 py-3 rounded-2xl font-bold text-sm transition-all duration-300 hover:scale-[1.015] active:scale-[0.99] group cursor-pointer border"
                    style={{
                      background: "var(--surface)",
                      borderColor: `${color}45`,
                      boxShadow: `0 8px 30px -8px ${color}25`,
                    }}
                  >
                    {/* Hover ambient color wash */}
                    <div
                      className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                      style={{
                        background: `linear-gradient(90deg, transparent 0%, ${color}14 50%, transparent 100%)`,
                      }}
                    />

                    <div className="flex items-center gap-2.5 sm:gap-3 relative z-10 text-left">
                      <div
                        className="w-2.5 h-2.5 rounded-full animate-pulse shrink-0"
                        style={{ background: color, boxShadow: `0 0 10px ${color}` }}
                      />
                      <span className="text-xs sm:text-sm font-bold tracking-tight transition-colors" style={{ color: "var(--txt)" }}>
                        Try this with your own dataset
                      </span>
                      <span className="text-xs transition-transform duration-200 group-hover:translate-x-1 font-bold" style={{ color: color }}>
                        →
                      </span>
                    </div>

                    {/* Standout Dynamic Upload Button */}
                    <div
                      className="relative z-10 flex items-center gap-2 px-3.5 sm:px-4 py-2 rounded-xl text-white font-black text-xs tracking-wide shadow-md transition-all duration-300 group-hover:scale-105 group-hover:shadow-xl shrink-0"
                      style={{
                        background: `linear-gradient(135deg, ${color} 0%, ${getStageGradientEnd(color)} 100%)`,
                        boxShadow: `0 4px 18px ${color}65, 0 0 10px ${color}35`,
                      }}
                    >
                      <UploadCloud size={14} className="group-hover:-translate-y-0.5 transition-transform duration-200" />
                      <span>Upload</span>
                    </div>
                  </button>
                </div>
              </div>

              {/* dots */}
              <div className="flex items-center justify-center gap-2 mt-4">
                {PIPELINE_STAGES.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleStageSelect(i)}
                    className="rounded-full transition-all duration-300 cursor-pointer"
                    style={{
                      width: active === i ? "24px" : "8px",
                      height: "8px",
                      background:
                        active === i
                          ? s.color
                          : i < active
                            ? s.color + "55"
                            : "var(--border)",
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════════════════ */
export default function Home() {
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [showLaunchModal, setShowLaunchModal] = useState(false);
  const [launchConnectorId, setLaunchConnectorId] = useState<string | undefined>(undefined);
  const [uploadAlert, setUploadAlert] = useState(false);
  const [showSplash, setShowSplash] = useState(true);
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("login") === "1") {
        setShowLoginModal(true);
        window.history.replaceState({}, "", "/");
      }
      if (params.get("launch") === "1" || params.get("ingest") === "1" || params.get("upload") === "1") {
        setShowLaunchModal(true);
        window.history.replaceState({}, "", "/");
      }
      if (params.get("upload_required") === "1") {
        setShowLaunchModal(true);
        window.history.replaceState({}, "", "/");
      }
      if (params.get("login_success") === "1") {
        setShowSplash(true);
        window.history.replaceState({}, "", "/");
      }

      // Clean up multiple concatenated hashes (e.g. #audiences#origin -> #origin)
      if (window.location.hash) {
        const hashParts = window.location.hash.split("#").filter(Boolean);
        if (hashParts.length > 1) {
          const cleanHash = hashParts[hashParts.length - 1];
          window.history.replaceState({}, "", `/#${cleanHash}`);
          setTimeout(() => {
            document.getElementById(cleanHash)?.scrollIntoView({ behavior: "smooth" });
          }, 100);
        }
      }
    }
  }, []);

  const fadeUp = {
    hidden: { opacity: 0, y: 28 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.55, ease: "easeOut" as const },
    },
  };

  const handleLaunchWorkspace = (connectorId?: string) => {
    setLaunchConnectorId(connectorId);
    setShowLaunchModal(true);
  };

  return (
    <div
      className="relative min-h-screen flex flex-col selection:bg-orange-500/30 selection:text-white transition-colors duration-300"
      style={{ background: "var(--bg)", color: "var(--txt)" }}
    >
      {/* Subtle Noise Texture & Ambient Background Mesh */}
      <div className="noise" />
      <div className="mesh" />

      {/* Splash screen */}
      {showSplash && (
        <SplashLoader isLoading={loading} onComplete={() => setShowSplash(false)} />
      )}

      {/* Login Modal */}
      {showLoginModal && (
        <LoginModal onClose={() => setShowLoginModal(false)} />
      )}

      {/* Universal Workspace Launch & Ingestion Modal */}
      <WorkspaceLaunchModal
        isOpen={showLaunchModal}
        onClose={() => {
          setShowLaunchModal(false);
          setLaunchConnectorId(undefined);
        }}
        initialConnectorId={launchConnectorId}
      />

      {/* Floating Upload Requirement Alert */}
      {uploadAlert && (
        <div
          className="fixed top-6 left-1/2 -translate-x-1/2 w-[340px] max-w-[90vw] z-[9999] px-4 py-3 rounded-2xl flex items-center gap-3 shadow-2xl backdrop-blur-xl border transition-all animate-slideUp"
          style={{
            background: "rgba(15, 12, 10, 0.95)",
            borderColor: "rgba(245, 158, 11, 0.4)",
          }}
        >
          <AlertTriangle size={18} className="text-amber-500 flex-shrink-0" />
          <div className="flex-1 text-left">
            <p className="text-xs font-bold" style={{ color: "var(--txt)" }}>
              Dataset Required
            </p>
            <p className="text-[11px] opacity-80" style={{ color: "var(--txt-m)" }}>
              Please ingest a dataset to access the workspace.
            </p>
          </div>
          <button
            onClick={() => setUploadAlert(false)}
            className="p-1 rounded-lg opacity-60 hover:opacity-100 transition-opacity"
            style={{ color: "var(--txt-m)" }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Navigation */}
      <Header
        onLoginClick={() => setShowLoginModal(true)}
        onLaunchWorkspace={() => setShowLaunchModal(true)}
      />

      <main className="flex-1 w-full flex flex-col">
        {/* ══════════════ HERO ══════════════ */}
        <section className="relative overflow-hidden min-h-[calc(100dvh-64px)] min-h-[calc(100vh-64px)] flex flex-col justify-center items-center px-4 sm:px-8 py-6 sm:py-10 md:py-12">
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            <div
              className="w-[300px] sm:w-[600px] h-[300px] sm:h-[600px] rounded-full filter blur-[100px] sm:blur-[140px] opacity-[0.14] transition-colors duration-500"
              style={{ background: "var(--accent)" }}
            />
          </div>

          <div className="relative z-10 w-full max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-6 lg:gap-10 items-center my-auto">
            {/* Left side: Text & CTA */}
            <div className="flex flex-col items-start text-left gap-4 sm:gap-6 w-full max-w-xl md:max-w-none">
              <motion.div
                initial="hidden"
                animate="visible"
                variants={fadeUp}
                className="flex flex-col items-start w-full"
              >
                <h1
                  className="text-[2.1rem] xs:text-[2.6rem] sm:text-5xl md:text-[2.75rem] lg:text-5xl xl:text-6xl font-black leading-[1.08] tracking-tight mb-3 sm:mb-5 transition-colors duration-300"
                  style={{ color: "var(--txt)" }}
                >
                  <span className="whitespace-nowrap">Turning Messy</span><br />
                  Data<br />
                  Into <span style={{ color: "var(--accent)" }}>Clear</span><br />
                  <span style={{ color: "var(--accent)" }}>Decisions.</span>
                </h1>
                <p
                  className="max-w-lg text-sm sm:text-base md:text-lg lg:text-xl leading-relaxed transition-colors duration-300"
                  style={{ color: "var(--txt-m)" }}
                >
                  Transform raw spreadsheets into statistical insights, predictive models, and executive reports <Scratch>without code.</Scratch>
                </p>
              </motion.div>

              <motion.div
                initial="hidden"
                animate="visible"
                variants={fadeUp}
                className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto"
              >
                <button
                  type="button"
                  onClick={() => handleLaunchWorkspace()}
                  className="w-full sm:w-auto justify-center px-6 py-3.5 sm:py-3 rounded-xl text-sm font-bold flex items-center gap-2 shadow-lg hover:scale-105 active:scale-[0.98] transition-all duration-200 cursor-pointer"
                  style={{ background: "var(--accent)", color: "#fff" }}
                >
                  Launch Workspace <ArrowRight size={16} />
                </button>
                <a
                  href="#pipeline"
                  className="w-full sm:w-auto justify-center text-center px-5 py-3.5 sm:py-3 rounded-xl text-sm font-bold border hover:border-[var(--accent)] active:scale-[0.98] transition-all duration-200"
                  style={{
                    borderColor: "var(--border)",
                    background: "var(--card-bg)",
                    color: "var(--txt)",
                  }}
                >
                  See How It Works
                </a>
              </motion.div>


            </div>

            {/* Right side: Three.js & GSAP 3D Hero Visual — Hidden on mobile screens */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={fadeUp}
              className="hidden md:flex w-full items-center justify-center relative"
            >
              <ThreeHeroVisual />
            </motion.div>
          </div>
        </section>

        {/* ══════════════ ABOUT / ORIGIN STORY ══════════════ */}
        <section id="about" className="pt-2 pb-12 sm:py-16 md:py-20 px-4 sm:px-8 relative">
          <span id="origin" className="sr-only" />
          <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-8 lg:gap-12 items-center">
            {/* Left side: Text */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={fadeUp}
              className="flex flex-col gap-6 max-w-xl text-left"
            >
              <span
                className="text-[11px] font-extrabold uppercase tracking-widest"
                style={{ color: "var(--accent)" }}
              >
                About
              </span>
              <h2
                className="text-3xl sm:text-5xl font-black tracking-tight leading-tight transition-colors duration-300"
                style={{ color: "var(--txt)" }}
              >
                Why We Built DataForge
              </h2>
              <div
                className="flex flex-col gap-5 text-base sm:text-lg leading-relaxed text-left transition-colors duration-300"
                style={{ color: "var(--txt-m)" }}
              >
                <p>
                  Every day, organisations, researchers and students drown in
                  spreadsheets. Turning raw rows into meaningful answers is still
                  a tedious, error-prone chore: traditional tools demand manual
                  formulas, while advanced platforms require programming expertise.
                </p>
                <p>
                  We built DataForge to close that gap. By automating the entire
                  analytical lifecycle (from missing-value imputation and outlier
                  detection to AutoML model training and PDF generation), DataForge
                  delivers{" "}
                  <Scratch>enterprise-grade insights in seconds.</Scratch>
                </p>
                <p>
                  The result: a unified platform where no-code users and
                  professional analysts work side-by-side, making decisions
                  backed by <Scratch>real statistical evidence.</Scratch>
                </p>
              </div>
            </motion.div>

            {/* Right side: Abstract UI Composition (Chaos vs Clarity) */}
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={fadeUp}
              className="relative w-full max-w-sm sm:max-w-md mx-auto aspect-square flex items-center justify-center"
            >
              {/* Background glow */}
              <div
                className="absolute inset-0 bg-gradient-to-tr from-transparent opacity-[0.1] rounded-full blur-[100px]"
                style={{
                  backgroundImage:
                    "radial-gradient(circle at top right, var(--accent), transparent)",
                }}
              />

              {/* Back Card: Messy Spreadsheet (The Problem) */}
              <motion.div
                animate={{ y: [-8, 8, -8], rotate: [-2, -1, -2] }}
                transition={{
                  duration: 7,
                  repeat: Infinity,
                  ease: "easeInOut",
                }}
                className="absolute top-[8%] left-[0%] w-[75%] rounded-xl border p-5 shadow-xl flex flex-col gap-2"
                style={{
                  background: "var(--bg)",
                  borderColor: "var(--border)",
                  opacity: 0.5,
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-3 h-3 rounded-full bg-red-500/40" />
                  <div className="w-3 h-3 rounded-full bg-amber-400/40" />
                  <div className="w-3 h-3 rounded-full bg-green-500/40" />
                  <div className="ml-2 w-20 h-2 bg-red-500/20 rounded-full" />
                </div>
                {/* Spreadsheet grid */}
                {[...Array(6)].map((_, r) => (
                  <div key={r} className="grid grid-cols-5 gap-1.5">
                    {[...Array(5)].map((_, c) => (
                      <div
                        key={c}
                        className="h-4 rounded-sm border"
                        style={{
                          borderColor: "var(--border)",
                          background:
                            (r === 2 && c === 3) || (r === 4 && c === 1)
                              ? "rgba(239, 68, 68, 0.2)"
                              : "var(--card-bg)",
                        }}
                      />
                    ))}
                  </div>
                ))}
              </motion.div>

              {/* Front Card: Clear Insight (The Solution) */}
              <motion.div
                animate={{ y: [8, -8, 8], rotate: [1, 2, 1] }}
                transition={{
                  duration: 6,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: 1,
                }}
                className="absolute bottom-[10%] right-[0%] w-[85%] rounded-xl border p-6 sm:p-8 shadow-2xl backdrop-blur-xl flex flex-col gap-5"
                style={{
                  background: "var(--card-bg)",
                  borderColor: "var(--accent)",
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center"
                      style={{ background: "var(--accent)", color: "#000" }}
                    >
                      <Wand2 size={20} />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <div
                        className="w-24 h-2.5 rounded-full"
                        style={{ background: "var(--txt)" }}
                      />
                      <div
                        className="w-16 h-2 rounded-full"
                        style={{ background: "var(--txt-m)" }}
                      />
                    </div>
                  </div>
                  <div className="px-2.5 py-1 rounded text-[10px] font-extrabold uppercase tracking-wider text-green-400 bg-green-400/10 border border-green-400/20">
                    High Confidence
                  </div>
                </div>

                {/* Abstract Bar Chart */}
                <div className="flex items-end gap-2 h-28 mt-2">
                  {[30, 50, 40, 70, 55, 100].map((h, i) => (
                    <div
                      key={i}
                      className="flex-1 rounded-t-md transition-all duration-500 relative group"
                      style={{
                        height: `${h}%`,
                        background: i === 5 ? "var(--accent)" : "var(--border)",
                      }}
                    >
                      {i === 5 && (
                        <div
                          className="absolute -top-3 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full"
                          style={{ background: "var(--accent)" }}
                        />
                      )}
                    </div>
                  ))}
                </div>

                {/* Insight Text */}
                <div className="flex flex-col gap-2 mt-2">
                  <div
                    className="w-full h-2.5 rounded-full opacity-40"
                    style={{ background: "var(--txt)" }}
                  />
                  <div
                    className="w-4/5 h-2.5 rounded-full opacity-40"
                    style={{ background: "var(--txt)" }}
                  />
                </div>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ══════════════ CTA BANNER (Above How It Works) ══════════════ */}
        <div className="max-w-6xl mx-auto px-4 sm:px-6 my-6 sm:my-8">
          <CTABanner
            variant="compact"
            title="Test DataForge with your dataset"
            subtitle="Free plan — zero setup, instant automated EDA."
            buttonText="Launch Workspace"
            onAction={handleLaunchWorkspace}
            secondaryButtonText="Architecture"
            secondaryHref="/#about"
          />
        </div>

        {/* ══════════════ PIPELINE ══════════════ */}
        <section id="pipeline">
          <PipelineShowcase onTryDataset={handleLaunchWorkspace} />
        </section>

        {/* ══════════════ WHO USES DATAFORGE ══════════════ */}
        <BuiltFor />

        {/* ══════════════ TEAM ══════════════ */}
        <section id="team" className="py-8 relative">
          <span id="meet-the-builders" className="sr-only" />
          <TeamSection />
        </section>
      </main>

      {/* ══════════════ BOTTOM CTA BANNER (Compact Variant) ══════════════ */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 mb-12 sm:mb-16">
        <CTABanner
          variant="compact"
          title="Ready to experience DataForge with your own data?"
          subtitle="Instant statistical EDA, data quality scoring, and automated model benchmarks in ~60 seconds."
          buttonText="Launch Workspace"
          onAction={handleLaunchWorkspace}
          secondaryButtonText="View Pricing Plans"
          secondaryHref="/pricing"
        />
      </div>

      <Footer />
    </div>
  );
}
