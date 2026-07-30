"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import Header from "../components/landing/Header";
import Footer from "../components/landing/Footer";
import LoginModal from "../components/landing/LoginModal";
import TeamSection from "../components/landing/TeamSection";
import {
  Sparkles,
  Database,
  Wand2,
  Cpu,
  MessageSquareCode,
  FileText,
  UploadCloud,
  ArrowRight,
  Clock,
  LayoutGrid,
  FileSpreadsheet,
  AlertTriangle,
  Server,
  Key,
  Globe,
  Bot,
  PieChart,
  HardDrive,
  Zap,
  HelpCircle,
  CheckCircle2,
  Compass,
  Activity,
  ShieldCheck,
  LineChart,
  Target,
  BarChart4
} from "lucide-react";

export default function AboutPage() {
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [activePetal, setActivePetal] = useState<number | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      if (new URLSearchParams(window.location.search).get("login") === "1") {
        setShowLoginModal(true);
        window.history.replaceState({}, "", "/about");
      }
    }
  }, []);

  const fadeIn = {
    hidden: { opacity: 0, y: 24 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } }
  };

  const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.12
      }
    }
  };

  // 6 Petals for the Interactive Radial Infographic
  const PETALS = [
    {
      num: "01",
      title: "Ingest",
      name: "Smart Dataset Import",
      icon: UploadCloud,
      color: "#FF5722",
      glow: "rgba(255, 87, 34, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(255, 87, 34, 0.15), rgba(255, 87, 34, 0.03))",
      borderColor: "rgba(255, 87, 34, 0.4)",
      shortDesc: "Securely ingest CSV, Excel, or Google Sheets with automatic delimiter detection & schema resolution."
    },
    {
      num: "02",
      title: "Clean",
      name: "Automated Preprocessing",
      icon: Wand2,
      color: "#EF4444",
      glow: "rgba(239, 68, 68, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.03))",
      borderColor: "rgba(239, 68, 68, 0.4)",
      shortDesc: "Automatically detect and impute missing values, remove duplicates, trim whitespace, and clean Z-score outliers."
    },
    {
      num: "03",
      title: "Analyze",
      name: "Deterministic Insights",
      icon: Activity,
      color: "#3B82F6",
      glow: "rgba(59, 130, 246, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.03))",
      borderColor: "rgba(59, 130, 246, 0.4)",
      shortDesc: "Statistical algorithms discover linear trends, Pearson correlations, anomaly spikes, and category rankings."
    },
    {
      num: "04",
      title: "Ask AI",
      name: "Natural Language Chat",
      icon: MessageSquareCode,
      color: "#6366F1",
      glow: "rgba(99, 102, 241, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.03))",
      borderColor: "rgba(99, 102, 241, 0.4)",
      shortDesc: "Query your dataset in plain English with Google Gemini LLM to receive instant answers and chart formulas."
    },
    {
      num: "05",
      title: "Predict",
      name: "AutoML & Explainability",
      icon: Cpu,
      color: "#A855F7",
      glow: "rgba(168, 85, 247, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(168, 85, 247, 0.03))",
      borderColor: "rgba(168, 85, 247, 0.4)",
      shortDesc: "Train FLAML machine learning models with automated feature importance ranking powered by SHAP values."
    },
    {
      num: "06",
      title: "Report",
      name: "Executive PDF Exports",
      icon: FileText,
      color: "#F59E0B",
      glow: "rgba(245, 158, 11, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.03))",
      borderColor: "rgba(245, 158, 11, 0.4)",
      shortDesc: "Generate comprehensive EDA profiling reports, executive PDF downloads, and shareable dashboards."
    }
  ];

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden" style={{ background: "var(--bg)", color: "var(--txt)" }}>
      {/* Background ambient overlays */}
      <div className="noise"></div>
      <div className="mesh"></div>

      {showLoginModal && (
        <LoginModal onClose={() => setShowLoginModal(false)} />
      )}

      {/* Navigation Header */}
      <Header onLoginClick={() => setShowLoginModal(true)} />

      {/* Main Container with elevated vertical breathing room */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-5 sm:px-8 md:px-12 py-6 sm:py-10 md:py-16 flex flex-col gap-20 md:gap-32">

        {/* ====================================================================
            SECTION 1: Hero Section — Story & Vision
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="flex flex-col items-center text-center pt-2 md:pt-6 max-w-4xl mx-auto"
        >
          {/* Status Badge */}
          <div
            className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full border text-[11px] font-extrabold uppercase tracking-widest mb-6 shadow-sm"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--accent)"
            }}
          >
            <Sparkles size={14} className="animate-pulse" />
            <span>DataForge Engine v3.0 · Automated Analytics</span>
          </div>

          {/* Primary Hero Title */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[1.12] mb-6">
            Turning Messy Datasets Into <br />
            <span
              className="inline-block bg-gradient-to-r from-[var(--accent)] via-blue-600 to-indigo-600 bg-clip-text text-transparent pb-1"
              style={{
                background: "linear-gradient(135deg, var(--accent) 0%, #2563eb 50%, #4f46e5 100%)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                WebkitTextFillColor: "transparent",
                color: "var(--accent)"
              }}
            >
              Executive Intelligence
            </span>
          </h1>

          {/* Hero Narrative Text */}
          <p className="max-w-3xl text-base sm:text-lg md:text-xl leading-relaxed font-normal mb-10" style={{ color: "var(--txt-m)" }}>
            DataForge is an automated data science platform engineered to eliminate manual spreadsheet bottlenecks.
            From dataset cleaning and statistical insight discovery to AutoML predictive modeling and natural language AI queries—DataForge transforms raw files into decision-ready executive reports in seconds.
          </p>

          {/* Call to Action Buttons */}
          <div className="flex items-center gap-4 flex-wrap justify-center mb-12">
            <Link
              href="/workspace"
              className="px-8 py-4 rounded-xl text-xs font-extrabold uppercase tracking-wider transition-all duration-200 shadow-2xl flex items-center gap-2.5 hover:scale-105"
              style={{ background: "var(--accent)", color: "#ffffff" }}
            >
              <span>Launch Workspace</span>
              <ArrowRight size={16} />
            </Link>
            <a
              href="#platform-architecture"
              className="px-7 py-4 rounded-xl text-xs font-extrabold uppercase tracking-wider border transition-all duration-200 flex items-center gap-2 hover:border-[var(--accent)]"
              style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--txt)" }}
            >
              <span>Explore Engine Architecture</span>
            </a>
          </div>

          {/* Quick Metrics Ribbon */}
          <div className="w-full grid grid-cols-2 sm:grid-cols-4 gap-4 p-5 rounded-2xl border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            {[
              { label: "Pipeline Speed", val: "10x Faster", sub: "Automated cleaning & EDA" },
              { label: "Data Quality", val: "100% Auto", sub: "Imputation & outlier bounds" },
              { label: "AI Intelligence", val: "Gemini 2.5", sub: "Natural language querying" },
              { label: "Predictive Models", val: "FLAML AutoML", sub: "With SHAP explainability" }
            ].map((m, idx) => (
              <div key={idx} className="flex flex-col items-center text-center p-2">
                <span className="text-xl sm:text-2xl font-black" style={{ color: "var(--accent)" }}>{m.val}</span>
                <span className="text-xs font-extrabold mt-0.5" style={{ color: "var(--txt)" }}>{m.label}</span>
                <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>{m.sub}</span>
              </div>
            ))}
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 2: Chapter 01 — Our Mission & Origin Story
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="gc rounded-3xl p-8 sm:p-12 md:p-16 relative overflow-hidden"
          style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        >
          <div className="max-w-3xl mx-auto flex flex-col gap-6">
            <div className="flex items-center gap-2">
              <Compass size={20} style={{ color: "var(--accent)" }} />
              <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
                Chapter 01 · Origin Story
              </span>
            </div>

            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              Why We Engineered DataForge
            </h2>

            <div className="text-base sm:text-lg leading-relaxed flex flex-col gap-5" style={{ color: "var(--txt-m)" }}>
              <p>
                Every single day, organizations, researchers, and students generate massive volumes of spreadsheet data. Yet, turning raw rows into meaningful answers remains a tedious, error-prone chore. Traditional software forces users into manual formula crafting, while advanced data science tools demand expertise in Python, R, or SQL.
              </p>
              <p>
                We built DataForge to eliminate this technical divide. Conceived as both an academic breakthrough and a practical engineering solution, DataForge unifies automated data preprocessing, statistical insight discovery, predictive machine learning, and AI chat into a seamless web platform.
              </p>
              <p>
                By automating the heavy lifting—from missing value imputation and Z-score outlier detection to FLAML model training and WeasyPrint executive PDF generation—DataForge empowers non-technical users and data analysts alike to derive enterprise-grade insights in seconds.
              </p>
            </div>
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 3: Chapter 02 — The Real-World Problems We Solve
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="flex flex-col gap-12"
        >
          <div className="text-center max-w-3xl mx-auto flex flex-col gap-3">
            <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
              Chapter 02 · Analytics Friction
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              The Challenges We Solve
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Traditional data workflows break down due to manual bottlenecks, fragmented software, and complex statistical code.
            </p>
          </div>

          <motion.div
            variants={staggerContainer}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {[
              {
                icon: FileSpreadsheet,
                title: "Corrupted & Messy Files",
                desc: "Raw CSV and Excel files contain missing values, duplicate entries, inconsistent date strings, and bad data types that corrupt analytics."
              },
              {
                icon: Clock,
                title: "Manual & Slow Workflows",
                desc: "Analysts spend over 80% of their time writing repetitive formulas, filtering columns manually, and copying charts into slide decks."
              },
              {
                icon: AlertTriangle,
                title: "Steep Technical Barriers",
                desc: "Advanced statistical modeling and machine learning traditionally require writing complex Python packages (Pandas, Scikit-Learn, Statsmodels)."
              },
              {
                icon: HelpCircle,
                title: "Hidden Insights & Patterns",
                desc: "Raw numbers don't tell stories automatically. Identifying key anomalies, linear trends, and correlation matrices takes specialized statistics."
              },
              {
                icon: LayoutGrid,
                title: "Tool Fragmentation",
                desc: "Juggling separate applications for data cleaning, graphing, AI assistance, and PDF reporting creates friction and data loss."
              },
              {
                icon: ShieldCheck,
                title: "Black-Box Machine Learning",
                desc: "Standard predictive models give numbers without explanations. DataForge uses SHAP values to explain feature importance clearly."
              }
            ].map((problem, idx) => (
              <motion.div
                key={idx}
                variants={fadeIn}
                className="gc p-6 sm:p-8 rounded-2xl flex flex-col gap-4 transition-all duration-300 hover:-translate-y-1.5 border"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: "rgba(255, 67, 16, 0.1)", color: "var(--accent)" }}
                >
                  <problem.icon size={24} />
                </div>
                <h3 className="text-lg font-extrabold" style={{ color: "var(--txt)" }}>
                  {problem.title}
                </h3>
                <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--txt-m)" }}>
                  {problem.desc}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </motion.section>

        {/* ====================================================================
            SECTION 4: Chapter 03 — The DataForge Advantage (Our Solution)
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="gc rounded-3xl p-8 sm:p-12 md:p-16 relative overflow-hidden"
          style={{
            background: "linear-gradient(135deg, var(--surface) 0%, var(--card) 100%)",
            border: "1px solid var(--border)"
          }}
        >
          <div className="max-w-3xl mx-auto flex flex-col gap-8">
            <div className="flex flex-col gap-3">
              <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
                Chapter 03 · Unified Intelligence
              </span>
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
                The DataForge Solution
              </h2>
            </div>

            <p className="text-base sm:text-lg leading-relaxed" style={{ color: "var(--txt-m)" }}>
              DataForge orchestrates the complete analytical lifecycle inside a single web workspace. Simply upload your dataset and receive complete end-to-end intelligence:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {[
                { title: "Automated Data Preprocessing", text: "Imputes missing numerical & categorical values, drops duplicates, and standardizes formats automatically." },
                { title: "Deterministic Statistical Engine", text: "Detects Z-score anomalies, Pearson correlation matrices, trend lines, and contribution breakdowns." },
                { title: "Natural Language AI Querying", text: "Chat with your dataset in plain English powered by Google Gemini 2.5 Flash LLM." },
                { title: "AutoML & SHAP Explainability", text: "Trains predictive models using FLAML and generates interpretable SHAP feature rankings." }
              ].map((sol, i) => (
                <div key={i} className="flex items-start gap-4 p-5 rounded-2xl border" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
                  <CheckCircle2 size={22} className="shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                  <div>
                    <h4 className="text-sm font-extrabold" style={{ color: "var(--txt)" }}>{sol.title}</h4>
                    <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--txt-m)" }}>{sol.text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 5: Chapter 04 — How DataForge Works (Process & Interactive Pipeline)
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="flex flex-col gap-12"
        >
          <div className="text-center max-w-3xl mx-auto flex flex-col gap-3">
            <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
              Chapter 04 · System Pipeline
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              How DataForge Works
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              From raw dataset ingestion to executive PDF reports in 6 automated stages.
            </p>
          </div>

          {/* Workflow Stage Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { step: "01", title: "Upload", icon: UploadCloud },
              { step: "02", title: "Clean", icon: Wand2 },
              { step: "03", title: "Analyze", icon: Sparkles },
              { step: "04", title: "Ask AI", icon: MessageSquareCode },
              { step: "05", title: "Model", icon: Cpu },
              { step: "06", title: "Report", icon: FileText }
            ].map((item, idx) => (
              <div
                key={idx}
                className="gc p-4 rounded-xl flex flex-col items-center text-center gap-3 border transition-transform hover:-translate-y-1"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <span className="text-[10px] font-black px-2.5 py-0.5 rounded-full" style={{ background: "rgba(255, 67, 16, 0.12)", color: "var(--accent)" }}>
                  {item.step}
                </span>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: "var(--bg)", color: "var(--txt)" }}>
                  <item.icon size={20} />
                </div>
                <span className="text-xs font-extrabold" style={{ color: "var(--txt)" }}>
                  {item.title}
                </span>
              </div>
            ))}
          </div>

          {/* Live Data Processing Pipeline Interactive Diagram */}
          <div className="gc p-6 sm:p-10 rounded-3xl flex flex-col items-center gap-6 text-center border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <div className="w-full max-w-4xl mx-auto rounded-2xl p-6 sm:p-8 border shadow-xl flex flex-col gap-6" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
              <div className="flex items-center justify-between border-b pb-4 flex-wrap gap-2" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs font-black uppercase tracking-widest" style={{ color: "var(--txt)" }}>DataForge Automated Engine Architecture</span>
                </div>
                <span className="text-[10px] font-extrabold uppercase tracking-widest px-2.5 py-0.5 rounded-full" style={{ background: "rgba(255,67,16,0.12)", color: "var(--accent)" }}>
                  Verified Execution Flow
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-left">
                {[
                  { step: "1", title: "Raw Data Ingestion", desc: "CSV, Excel & Google Sheets parsing into Pandas DataFrames", color: "#FF5722" },
                  { step: "2", title: "Smart Cleaning", desc: "Median/Mode imputation, duplicate removal & Z-score bounds", color: "#EF4444" },
                  { step: "3", title: "Analytical Engine", desc: "Regression trends, Pearson correlations & Holt-Winters forecasting", color: "#3B82F6" },
                  { step: "4", title: "Executive Output", desc: "Interactive Chart.js dashboards & WeasyPrint PDF reports", color: "#10B981" }
                ].map((item, idx) => (
                  <div key={idx} className="p-4 rounded-xl border flex flex-col gap-2 relative overflow-hidden" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                    <div className="w-2 h-2 rounded-full absolute top-3 right-3" style={{ background: item.color }} />
                    <span className="text-[10px] font-black uppercase tracking-wider" style={{ color: item.color }}>Stage 0{item.step}</span>
                    <h4 className="text-xs sm:text-sm font-black" style={{ color: "var(--txt)" }}>{item.title}</h4>
                    <p className="text-[11px] font-medium leading-normal" style={{ color: "var(--txt-m)" }}>{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
            <p className="text-xs sm:text-sm font-semibold max-w-lg" style={{ color: "var(--txt-m)" }}>
              What Happens After You Upload — DataForge securely ingests, cleans, analyzes, models, and generates interactive reports automatically.
            </p>
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 6: Chapter 05 — Core Capabilities (Radial Petals Infographic)
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="flex flex-col gap-16 py-4"
        >
          <div className="text-center max-w-3xl mx-auto flex flex-col gap-3">
            <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
              Chapter 05 · Core Capabilities
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              What You Can Do
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              The DataForge Engine orchestrates 6 interconnected capabilities around your uploaded dataset.
            </p>
          </div>

          {/* RADIAL PETAL INFOGRAPHIC */}
          <div className="relative w-full max-w-5xl mx-auto flex flex-col items-center">
            {/* Center Node */}
            <div className="relative z-20 mb-12 md:mb-16">
              <div
                className="w-48 h-48 sm:w-56 sm:h-56 rounded-full flex flex-col items-center justify-center text-center p-6 shadow-2xl transition-all duration-300 border-2"
                style={{
                  background: "radial-gradient(circle, var(--surface) 0%, var(--card) 100%)",
                  borderColor: "var(--accent)",
                  boxShadow: "0 0 40px var(--glow)"
                }}
              >
                <div className="w-10 h-10 rounded-full flex items-center justify-center mb-2" style={{ background: "rgba(255, 67, 16, 0.15)", color: "var(--accent)" }}>
                  <Database size={22} className="animate-spin" style={{ animationDuration: "12s" }} />
                </div>
                <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: "var(--accent)" }}>
                  DATAFORGE
                </span>
                <h3 className="text-xs sm:text-sm font-black uppercase tracking-tight mt-1 leading-snug" style={{ color: "var(--txt)" }}>
                  AUTOMATED ANALYTICS PIPELINE
                </h3>
                <span className="text-[10px] mt-1 opacity-70" style={{ color: "var(--txt-m)" }}>
                  6 Interconnected Modules
                </span>
              </div>
            </div>

            {/* Radial Petals Grid */}
            <div className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 relative z-10">
              {PETALS.map((petal, idx) => (
                <motion.div
                  key={idx}
                  whileHover={{ scale: 1.03, y: -4 }}
                  onMouseEnter={() => setActivePetal(idx)}
                  onMouseLeave={() => setActivePetal(null)}
                  className="gc p-6 rounded-2xl flex flex-col gap-3 relative overflow-hidden transition-all duration-300 border"
                  style={{
                    background: petal.bgGradient,
                    borderColor: activePetal === idx ? petal.color : "var(--border)",
                    boxShadow: activePetal === idx ? `0 8px 30px ${petal.glow}` : "none"
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className="text-xs font-black px-2.5 py-1 rounded-full text-white shadow-md"
                      style={{ background: petal.color }}
                    >
                      {petal.num}
                    </span>
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center"
                      style={{ background: "var(--surface)", color: petal.color, border: `1px solid ${petal.borderColor}` }}
                    >
                      <petal.icon size={20} />
                    </div>
                  </div>

                  <div className="mt-1">
                    <span className="text-[10px] font-extrabold uppercase tracking-widest" style={{ color: petal.color }}>
                      {petal.title}
                    </span>
                    <h4 className="text-base font-extrabold mt-0.5" style={{ color: "var(--txt)" }}>
                      {petal.name}
                    </h4>
                  </div>

                  <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                    {petal.shortDesc}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 7: Chapter 06 — Authentic Technology Stack
           ==================================================================== */}
        <motion.section
          id="platform-architecture"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="flex flex-col gap-12"
        >
          <div className="text-center max-w-3xl mx-auto flex flex-col gap-3">
            <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
              Chapter 06 · Architecture & Tech Stack
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              Behind the Scenes
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Verified, high-performance technologies powering DataForge based on real backend implementation:
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                category: "Frontend",
                name: "Next.js 16 & React 19",
                icon: Globe,
                desc: "Modern responsive web application built with App Router, TypeScript & Tailwind CSS."
              },
              {
                category: "Backend REST API",
                name: "FastAPI & Python 3.10+",
                icon: Server,
                desc: "High-throughput asynchronous Python server executing data cleaning and stats calculations."
              },
              {
                category: "AI Conversational",
                name: "Google Gemini 2.5 Flash",
                icon: Bot,
                desc: "Natural language query interpretation generating automated formulas & chart specifications."
              },
              {
                category: "AutoML & Explainability",
                name: "FLAML & SHAP Values",
                icon: Cpu,
                desc: "Automated model tuning and feature importance scoring for transparent predictions."
              },
              {
                category: "Database & Auth",
                name: "Supabase & OAuth 2.0",
                icon: Key,
                desc: "PostgreSQL database for users and project metadata with Google OAuth authentication."
              },
              {
                category: "Data Visualization",
                name: "Chart.js & React-Chartjs-2",
                icon: PieChart,
                desc: "Interactive line, bar, scatter, donut, and distribution charts with dark/light themes."
              },
              {
                category: "Cloud Storage & Queues",
                name: "Supabase Storage & Redis",
                icon: HardDrive,
                desc: "Encrypted file bucket storage for uploaded datasets with Redis task message queues."
              },
              {
                category: "Executive Reporting",
                name: "WeasyPrint & ydata-profiling",
                icon: Zap,
                desc: "Automated exploratory profiling and executive PDF report synthesis."
              }
            ].map((tech, idx) => (
              <div
                key={idx}
                className="gc p-6 rounded-2xl flex flex-col gap-3 border"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded border" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
                    {tech.category}
                  </span>
                  <tech.icon size={20} style={{ color: "var(--accent)" }} />
                </div>
                <h3 className="text-sm font-extrabold mt-1" style={{ color: "var(--txt)" }}>
                  {tech.name}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                  {tech.desc}
                </p>
              </div>
            ))}
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 8: Chapter 07 — Future Vision & Roadmap
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="flex flex-col gap-12"
        >
          <div className="text-center max-w-3xl mx-auto flex flex-col gap-3">
            <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
              Chapter 07 · Product Roadmap
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              What's Next?
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Future innovations planned for DataForge to expand automated data engineering:
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                status: "Phase 1: Active In-Progress",
                badgeColor: "#3B82F6",
                title: "Advanced Time-Series Forecasting",
                desc: "Expanding Holt-Winters and Prophet models for multi-variable trend forecasting and anomaly prediction."
              },
              {
                status: "Phase 2: Upcoming",
                badgeColor: "#8B5CF6",
                title: "Multi-Sheet & Table Joining",
                desc: "Automated relational joining and entity synthesis across multiple spreadsheet sheets and connected databases."
              },
              {
                status: "Phase 3: Horizon",
                badgeColor: "#EC4899",
                title: "Live Cloud Connectors",
                desc: "Direct integrations with Snowflake, BigQuery, AWS S3, and real-time streaming data sources."
              }
            ].map((item, idx) => (
              <div
                key={idx}
                className="gc p-6 sm:p-8 rounded-2xl flex flex-col gap-4 relative overflow-hidden border"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ background: item.badgeColor }}
                  />
                  <span className="text-[11px] font-extrabold uppercase tracking-wider" style={{ color: item.badgeColor }}>
                    {item.status}
                  </span>
                </div>
                <h3 className="text-base font-extrabold" style={{ color: "var(--txt)" }}>
                  {item.title}
                </h3>
                <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 9: Chapter 08 — Meet the Builders
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="pt-4"
        >
          <TeamSection />
        </motion.section>

      </main>

      {/* Footer */}
      <Footer />
    </div>
  );
}
