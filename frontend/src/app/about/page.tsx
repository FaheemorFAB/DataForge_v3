"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import Header from "../components/landing/Header";
import Footer from "../components/landing/Footer";
import LoginModal from "../components/landing/LoginModal";
import TeamSection from "../components/landing/TeamSection";
import {
  Sparkles,
  Database,
  Wand2,
  BarChart3,
  Cpu,
  MessageSquareCode,
  FileText,
  Download,
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
  Layers,
  Search,
  Activity,
  ArrowDown
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

  // 6 Petals for Section 6 (Flower Infographic)
  const PETALS = [
    {
      num: "01",
      title: "Ingest",
      name: "Upload Datasets",
      icon: UploadCloud,
      color: "#FF5722",
      glow: "rgba(255, 87, 34, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(255, 87, 34, 0.15), rgba(255, 87, 34, 0.03))",
      borderColor: "rgba(255, 87, 34, 0.4)",
      shortDesc: "Securely import CSV, Excel, or Google Sheets into an analysis-ready workspace."
    },
    {
      num: "02",
      title: "Clean",
      name: "Auto Preprocessing",
      icon: Wand2,
      color: "#EF4444",
      glow: "rgba(239, 68, 68, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.03))",
      borderColor: "rgba(239, 68, 68, 0.4)",
      shortDesc: "Automatically detect & fix missing values, remove duplicates, and trim formatting errors."
    },
    {
      num: "03",
      title: "Analyse",
      name: "AI Insights Engine",
      icon: Activity,
      color: "#3B82F6",
      glow: "rgba(59, 130, 246, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.03))",
      borderColor: "rgba(59, 130, 246, 0.4)",
      shortDesc: "Statistical algorithms discover anomalies, correlations, trends, and key metrics."
    },
    {
      num: "04",
      title: "Ask",
      name: "Natural Language AI",
      icon: MessageSquareCode,
      color: "#6366F1",
      glow: "rgba(99, 102, 241, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(99, 102, 241, 0.03))",
      borderColor: "rgba(99, 102, 241, 0.4)",
      shortDesc: "Ask questions in plain English and receive instant explanations and visual answers."
    },
    {
      num: "05",
      title: "Model",
      name: "AutoML Predictions",
      icon: Cpu,
      color: "#A855F7",
      glow: "rgba(168, 85, 247, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(168, 85, 247, 0.03))",
      borderColor: "rgba(168, 85, 247, 0.4)",
      shortDesc: "Train predictive machine learning models automatically with SHAP feature importance."
    },
    {
      num: "06",
      title: "Report",
      name: "Executive Reports",
      icon: FileText,
      color: "#F59E0B",
      glow: "rgba(245, 158, 11, 0.35)",
      bgGradient: "linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.03))",
      borderColor: "rgba(245, 158, 11, 0.4)",
      shortDesc: "Generate executive summary reports, PDF exports, and shareable dashboards instantly."
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

      {/* Main Container with generous SaaS vertical breathing room */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-5 sm:px-8 md:px-12 py-12 md:py-24 flex flex-col gap-24 md:gap-36">

        {/* ====================================================================
            SECTION 1: Welcome to Data Forge
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="flex flex-col items-center text-center pt-6 md:pt-12 max-w-4xl mx-auto"
        >
          <div
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border text-[11px] font-extrabold uppercase tracking-widest mb-8"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--accent)"
            }}
          >
            <Sparkles size={14} className="animate-pulse" />
            <span>Welcome to Data Forge</span>
          </div>

          <h1 className="text-4xl sm:text-6xl md:text-7xl font-black tracking-tight leading-[1.1] mb-8">
            Turn Raw Data Into <br />
            <span
              style={{
                background: "linear-gradient(135deg, var(--accent) 0%, #3b82f6 100%)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent"
              }}
            >
              Actionable Intelligence
            </span>
          </h1>

          <div className="max-w-3xl text-base sm:text-lg md:text-xl leading-relaxed flex flex-col gap-6 font-normal" style={{ color: "var(--txt-m)" }}>
            <p>
              Data Forge is an automated analytics platform engineered to transform messy datasets into decision-ready insights in minutes. Whether you are working with sales spreadsheets, research files, or customer exports, Data Forge simplifies your entire analytical workflow.
            </p>
            <p>
              Instead of spending hours writing complex formulas, cleaning broken rows, or writing code, Data Forge handles data cleaning, exploratory statistical analysis, dynamic charting, and predictive machine learning automatically.
            </p>
            <p>
              With built-in AI conversational querying, you can simply ask plain-English questions about your dataset, receive instant explanations, and export executive PDF reports without any technical expertise.
            </p>
          </div>

          <div className="mt-10 flex items-center gap-4 flex-wrap justify-center">
            <Link
              href="/dashboard"
              className="px-7 py-3.5 rounded-xl text-xs font-extrabold uppercase tracking-wider transition-all duration-200 shadow-xl flex items-center gap-2.5 hover:scale-105"
              style={{ background: "var(--accent)", color: "#ffffff" }}
            >
              <span>Launch Workspace</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 2: Why We Built Data Forge
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="gc rounded-3xl p-8 sm:p-12 md:p-16 relative overflow-hidden"
          style={{ background: "var(--surface)" }}
        >
          <div className="max-w-3xl mx-auto flex flex-col gap-6">
            <div className="flex items-center gap-2">
              <Compass size={20} style={{ color: "var(--accent)" }} />
              <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--txt-f)" }}>
                Our Purpose
              </span>
            </div>

            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              Why We Built Data Forge
            </h2>

            <div className="text-base sm:text-lg leading-relaxed flex flex-col gap-4" style={{ color: "var(--txt-m)" }}>
              <p>
                Every day, businesses, researchers, and students generate valuable data. Yet, deriving meaningful answers from spreadsheets remains a frustrating chore. Traditional tools either require manual calculations or demand steep technical skills in programming languages like Python and SQL.
              </p>
              <p>
                We created Data Forge to bridge this gap. Developed as an academic and practical innovation, our goal was to build an intelligent platform that makes data science accessible to everyone—from business analysts and product managers to academic researchers and students.
              </p>
              <p>
                By consolidating automated data cleaning, exploratory analysis, AI querying, and machine learning into a single web application, Data Forge empowers anyone to unlock the full value of their data with minimal effort.
              </p>
            </div>
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 3: The Problem We're Solving
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
              Real-World Challenges
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              The Problem We're Solving
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Data analytics often breaks down due to manual bottlenecks and complex software.
            </p>
          </div>

          <motion.div
            variants={staggerContainer}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {[
              {
                icon: FileSpreadsheet,
                title: "Messy Datasets",
                desc: "Raw files are filled with missing values, duplicate records, inconsistent naming, and incorrect data types that corrupt analysis."
              },
              {
                icon: Clock,
                title: "Manual & Slow Analysis",
                desc: "Users spend hours copying formulas, filtering columns manually, and creating basic charts from scratch."
              },
              {
                icon: AlertTriangle,
                title: "Overly Complex Software",
                desc: "Existing enterprise analytics tools require steep learning curves, expensive subscriptions, or deep coding knowledge."
              },
              {
                icon: HelpCircle,
                title: "Lack of Clear Insights",
                desc: "Raw numbers don't tell stories automatically. Identifying key trends, anomalies, and correlations takes specialized statistics."
              },
              {
                icon: LayoutGrid,
                title: "Fragmented Tooling",
                desc: "Switching between separate tools for cleaning, graphing, machine learning, and reporting causes delays and errors."
              }
            ].map((problem, idx) => (
              <motion.div
                key={idx}
                variants={fadeIn}
                className="gc p-6 rounded-2xl flex flex-col gap-4 transition-all duration-300 hover:-translate-y-1.5"
                style={{ background: "var(--surface)" }}
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
                <p className="text-sm leading-relaxed" style={{ color: "var(--txt-m)" }}>
                  {problem.desc}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </motion.section>

        {/* ====================================================================
            SECTION 4: Our Solution
           ==================================================================== */}
        <motion.section
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          variants={fadeIn}
          className="gc rounded-3xl p-8 sm:p-12 md:p-16 relative overflow-hidden"
          style={{
            background: "linear-gradient(135deg, var(--surface) 0%, var(--card) 100%)",
            borderColor: "var(--border)"
          }}
        >
          <div className="max-w-3xl mx-auto flex flex-col gap-8">
            <div className="flex flex-col gap-3">
              <span className="text-[11px] font-extrabold uppercase tracking-widest" style={{ color: "var(--accent)" }}>
                The Data Forge Advantage
              </span>
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
                Our Solution
              </h2>
            </div>

            <p className="text-base sm:text-lg leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Data Forge unifies the entire analytical lifecycle into a single, automated platform. Simply upload your dataset, and Data Forge delivers complete end-to-end intelligence:
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              {[
                { title: "Automated Data Cleaning", text: "Removes missing data, duplicate rows, and standardizes column types automatically." },
                { title: "Deterministic Insights", text: "Identifies anomalies (Z-score), trends (regression), and correlation matrices." },
                { title: "Natural Language AI Querying", text: "Chat with your dataset in plain English powered by Google Gemini 2.5 Flash." },
                { title: "AutoML & Explainable AI", text: "Trains predictive models automatically (FLAML) with SHAP feature importance." }
              ].map((sol, i) => (
                <div key={i} className="flex items-start gap-4 p-4 rounded-xl border" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
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
            SECTION 5: How Data Forge Works
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
              System Workflow
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              How Data Forge Works
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              From raw dataset ingestion to executive PDF reports in 6 simple stages.
            </p>
          </div>

          {/* Workflow Steps Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { step: "01", title: "Upload", icon: UploadCloud },
              { step: "02", title: "Clean", icon: Wand2 },
              { step: "03", title: "Analyse", icon: Sparkles },
              { step: "04", title: "Ask AI", icon: MessageSquareCode },
              { step: "05", title: "Model", icon: Cpu },
              { step: "06", title: "Report", icon: FileText }
            ].map((item, idx) => (
              <div
                key={idx}
                className="gc p-4 rounded-xl flex flex-col items-center text-center gap-3 relative transition-transform hover:-translate-y-1"
                style={{ background: "var(--surface)" }}
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

          {/* User Process Diagram Image Container */}
          <div className="gc p-6 sm:p-10 rounded-3xl flex flex-col items-center gap-6 text-center" style={{ background: "var(--surface)" }}>
            <div className="max-w-2xl mx-auto w-full rounded-2xl overflow-hidden shadow-2xl border" style={{ borderColor: "var(--border)" }}>
              <Image
                src="/dataforge-process.png"
                alt="What Happens After You Upload - Data Forge Process"
                width={900}
                height={900}
                className="w-full h-auto object-contain"
                priority
              />
            </div>
            <p className="text-xs sm:text-sm font-semibold max-w-lg" style={{ color: "var(--txt-m)" }}>
              What Happens After You Upload — DataForge securely ingests, cleans, analyzes, models, and generates interactive reports automatically.
            </p>
          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 6: What You Can Do (Key Features) — Flower-Style Infographic
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
              Core Capabilities
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              What You Can Do
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              The Data Forge Engine orchestrates 6 interconnected capabilities around your uploaded dataset.
            </p>
          </div>

          {/* FLOWER-STYLE RADIAL INFOGRAPHIC DISPLAY */}
          <div className="relative w-full max-w-5xl mx-auto flex flex-col items-center">

            {/* Center Circle Node */}
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
                  DATA FORGE
                </span>
                <h3 className="text-xs sm:text-sm font-black uppercase tracking-tight mt-1 leading-snug" style={{ color: "var(--txt)" }}>
                  WHAT HAPPENS AFTER YOU UPLOAD
                </h3>
                <span className="text-[10px] mt-1 opacity-70" style={{ color: "var(--txt-m)" }}>
                  Automated Analytics Engine
                </span>
              </div>
            </div>

            {/* Radial Petals Grid (Desktop & Tablet) */}
            <div className="w-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 relative z-10">
              {PETALS.map((petal, idx) => (
                <motion.div
                  key={idx}
                  whileHover={{ scale: 1.03, y: -4 }}
                  onMouseEnter={() => setActivePetal(idx)}
                  onMouseLeave={() => setActivePetal(null)}
                  className="gc p-6 rounded-2xl flex flex-col gap-3 relative overflow-hidden transition-all duration-300"
                  style={{
                    background: petal.bgGradient,
                    borderColor: activePetal === idx ? petal.color : "var(--border)",
                    boxShadow: activePetal === idx ? `0 8px 30px ${petal.glow}` : "none"
                  }}
                >
                  {/* Petal Badge & Icon */}
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

                  {/* Title & Name */}
                  <div className="mt-1">
                    <span className="text-[10px] font-extrabold uppercase tracking-widest" style={{ color: petal.color }}>
                      {petal.title}
                    </span>
                    <h4 className="text-base font-extrabold mt-0.5" style={{ color: "var(--txt)" }}>
                      {petal.name}
                    </h4>
                  </div>

                  {/* Short Description */}
                  <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                    {petal.shortDesc}
                  </p>
                </motion.div>
              ))}
            </div>

          </div>
        </motion.section>

        {/* ====================================================================
            SECTION 7: Behind the Scenes (Technology Stack)
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
              Architecture & Stack
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              Behind the Scenes
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Verified technologies powering Data Forge based on system implementation:
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                category: "Frontend",
                name: "Next.js 16 & React 19",
                icon: Globe,
                desc: "Modern responsive web interface built with App Router, TypeScript & Tailwind CSS."
              },
              {
                category: "Backend",
                name: "FastAPI & Python 3.10+",
                icon: Server,
                desc: "High-performance Python API handling data pipelines, statistics, and async tasks."
              },
              {
                category: "AI & ML",
                name: "Gemini 2.5 & FLAML",
                icon: Bot,
                desc: "Google Gemini 2.5 Flash LLM for queries, FLAML for AutoML, and SHAP values."
              },
              {
                category: "Database",
                name: "Supabase PostgreSQL",
                icon: Database,
                desc: "Relational database managing projects, metadata, user profiles, and logs."
              },
              {
                category: "Authentication",
                name: "Google OAuth 2.0",
                icon: Key,
                desc: "Secure user authentication using Authlib Google OAuth and JWT session tokens."
              },
              {
                category: "Visualization",
                name: "Chart.js & Canvas",
                icon: PieChart,
                desc: "Dynamic charts, heatmaps, distribution plots, and interactive dashboards."
              },
              {
                category: "Cloud & Storage",
                name: "Supabase Storage & Redis",
                icon: HardDrive,
                desc: "Encrypted dataset file buckets, Redis caching, and async task message queues."
              },
              {
                category: "Dev Tools",
                name: "Celery, ydata & WeasyPrint",
                icon: Zap,
                desc: "Automated exploratory profiling, background task queues, and executive PDF generation."
              }
            ].map((tech, idx) => (
              <div
                key={idx}
                className="gc p-6 rounded-2xl flex flex-col gap-3"
                style={{ background: "var(--surface)" }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded border" style={{ borderColor: "var(--border)", color: "var(--txt-f)" }}>
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
            SECTION 8: What's Next? (Future Vision & Roadmap)
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
              Product Roadmap
            </span>
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              What's Next?
            </h2>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              Future improvements planned for Data Forge based on academic research goals:
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                status: "Phase 1: In Progress",
                badgeColor: "#3B82F6",
                title: "Advanced Time-Series Forecasting",
                desc: "Implementing time-series models for trend prediction, seasonal forecasting, and future value estimation."
              },
              {
                status: "Phase 2: Up Next",
                badgeColor: "#8B5CF6",
                title: "Multi-Sheet & Multi-Table Synthesis",
                desc: "Automatic joining and synthesis across multiple spreadsheet sheets and connected database tables."
              },
              {
                status: "Phase 3: Future Horizon",
                badgeColor: "#EC4899",
                title: "Semi-Structured Data & Live Connectors",
                desc: "Expanding support to JSON/XML formats, Snowflake/BigQuery connectors, and mobile companion app."
              }
            ].map((item, idx) => (
              <div
                key={idx}
                className="gc p-6 sm:p-8 rounded-2xl flex flex-col gap-4 relative overflow-hidden"
                style={{ background: "var(--surface)" }}
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
            SECTION 9: Builders of Data Forge (Reusing Existing TeamSection)
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
