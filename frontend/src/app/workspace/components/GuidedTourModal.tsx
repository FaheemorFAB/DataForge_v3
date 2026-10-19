"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Table,
  Wand2,
  LayoutDashboard,
  Lightbulb,
  MessageSquare,
  Bot,
  ArrowRight,
  ArrowLeft,
  X,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
  FileText,
  Zap,
  Play,
  RotateCcw,
} from "lucide-react";

interface GuidedTourModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateTab: (tabId: string) => void;
  currentTab: string;
}

interface TourStep {
  step: number;
  tabId?: string;
  badge: string;
  icon: React.ElementType;
  title: string;
  subtitle: string;
  description: string;
  keyBenefits: string[];
  proTip: string;
  tryButtonText?: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    step: 1,
    badge: "Welcome to DataForge",
    icon: Sparkles,
    title: "Welcome! Data analytics without the headache.",
    subtitle: "Built for everyday business teams, not just data scientists.",
    description:
      "Think of DataForge as your automated spreadsheet assistant. You don't need to know Python, write SQL code, or remember formulas. We handle the heavy lifting so you can understand your numbers, spot trends, and make charts in under two minutes.",
    keyBenefits: [
      "Zero code required — everything works with 1 click",
      "Instant error fixing & missing value repair",
      "Plain-English explanations of all charts and trends",
      "Safe & private — your data stays strictly in your session",
    ],
    proTip: "You can't break anything here! Feel free to click around and test buttons.",
    tryButtonText: "Start the 60-second tour",
  },
  {
    step: 2,
    tabId: "preview",
    badge: "Step 1 of 6 · Data Table",
    icon: Table,
    title: "Your Data Table — Supercharged spreadsheet",
    subtitle: "Inspect, sort, and search all your records in one place.",
    description:
      "This is your home base. Just like Excel or Google Sheets, you can see every row and column. Click any column header to sort highest-to-lowest, or type anything into the search bar to find customer names, products, or dates instantly.",
    keyBenefits: [
      "Search across all columns simultaneously with instant results",
      "Click column headers to sort numbers, text, or dates",
      "Handles millions of rows smoothly without crashing your browser",
      "See column data quality and blank cell counters at a glance",
    ],
    proTip: "Notice a blank cell? No need to edit manually—our next step fixes it for you!",
    tryButtonText: "Jump to Data Table",
  },
  {
    step: 3,
    tabId: "cleaning",
    badge: "Step 2 of 6 · Clean & Fix",
    icon: Wand2,
    title: "1-Click Auto Clean — Your automatic repair shop",
    subtitle: "Fix blank cells, messy formats, and duplicate rows with zero code.",
    description:
      "Real-world data is almost always messy. With one click on 'Auto-Clean', DataForge automatically fills in missing numbers, standardizes date formats, trims accidental spaces, and scrubs duplicates. It even shows you a side-by-side preview so you see what changed before saving.",
    keyBenefits: [
      "Fills in blanks using intelligent averages and medians",
      "Standardizes messy dates and currency strings",
      "Removes duplicate entries and fixes text casing",
      "Always gives you an Undo option if you want to revert",
    ],
    proTip: "Always run 1-Click Auto Clean before making charts so your graphs don't have gaps.",
    tryButtonText: "Explore Clean & Fix",
  },
  {
    step: 4,
    tabId: "dashboard",
    badge: "Step 3 of 6 · Dashboards",
    icon: LayoutDashboard,
    title: "Dashboards — Executive charts ready for your boss",
    subtitle: "Turn boring rows into high-impact visuals in seconds.",
    description:
      "Ready to present to your manager, team, or clients? Pick from 12 chart types (Trend lines, Bar graphs, Donut charts, Heatmaps, and Waterfalls). Switch between curated color themes and download high-resolution PNG images ready to paste straight into your slides.",
    keyBenefits: [
      "Auto-generates recommended charts based on your columns",
      "Pick your favorite brand colors (Emerald, Cyberpunk, Indigo)",
      "Interactive zoom, tooltips, and hover values",
      "1-Click high-resolution PNG & SVG image downloads",
    ],
    proTip: "Try the 'Bar Chart' or 'Trend Line' first—they are the easiest way to see performance over time.",
    tryButtonText: "Open Dashboards",
  },
  {
    step: 5,
    tabId: "insights",
    badge: "Step 4 of 6 · Smart Insights",
    icon: Lightbulb,
    title: "Smart Insights — Plain-English explanations",
    subtitle: "No statistics degree needed to understand what's happening.",
    description:
      "Instead of squinting at complex tables, Smart Insights reads your numbers and tells you what they actually mean in human sentences. You'll see things like: 'Weekend sales are 38% higher than weekdays' or 'Revenue spikes in October due to promotion campaigns'.",
    keyBenefits: [
      "Automated trend detection & growth rate summaries",
      "Clear callouts for unusual spikes, drops, or anomalies",
      "Color-coded green (opportunities) and red (potential risks)",
      "Key performance drivers identified without statistical jargon",
    ],
    proTip: "Check the 'Key Driver' cards to see which factors impact your profit the most.",
    tryButtonText: "View Smart Insights",
  },
  {
    step: 6,
    tabId: "query",
    badge: "Step 5 of 6 · Ask AI",
    icon: MessageSquare,
    title: "Ask AI — Chat with your data in everyday English",
    subtitle: "Ask questions just like you're texting a helpful analyst.",
    description:
      "Ever wished you could just ask: 'Who were our top 5 customers last quarter?' or 'Which product has the highest return rate?' Type your question in normal English. The AI finds the answer, explains it, and even renders the chart right inside the chat.",
    keyBenefits: [
      "No SQL queries required — just speak naturally",
      "Instant answers with formatted summary tables",
      "Generates custom charts on the fly based on your questions",
      "Follow-up questions remembered in your chat history",
    ],
    proTip: "Try asking: 'Give me a 3-bullet summary of this dataset' for an instant overview!",
    tryButtonText: "Try Asking AI",
  },
  {
    step: 7,
    tabId: "automl",
    badge: "Step 6 of 6 · AutoML Training",
    icon: Bot,
    title: "AutoML — Train predictive models with ease",
    subtitle: "Train AI models to predict customer churn, revenue, or sales.",
    description:
      "Machine learning used to take teams of PhDs weeks to set up. In DataForge, you simply pick the column you want to predict (like 'Will Customer Churn?' or 'Next Month Revenue'). Click 'Train Models' and our tournament engine automatically finds the most accurate model for your data.",
    keyBenefits: [
      "Select your target column from a simple dropdown",
      "Automated model tournament compares LightGBM, Random Forest, & XGBoost",
      "Clear accuracy score so you know how reliable the prediction is",
      "Download a scored CSV with predictions attached to every row",
    ],
    proTip: "Great for predicting sales, loan approvals, employee retention, or lead scoring.",
    tryButtonText: "Explore AutoML",
  },
];

export function GuidedTourModal({
  isOpen,
  onClose,
  onNavigateTab,
  currentTab,
}: GuidedTourModalProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [dontShowAgain, setDontShowAgain] = useState(false);

  useEffect(() => {
    // Check if user previously checked "don't show again"
    const saved = localStorage.getItem("df_tour_seen");
    if (saved === "true") {
      setDontShowAgain(true);
    }
  }, []);

  const currentStep = TOUR_STEPS[currentStepIndex];
  const totalSteps = TOUR_STEPS.length;
  const isFirst = currentStepIndex === 0;
  const isLast = currentStepIndex === totalSteps - 1;

  const handleNext = () => {
    if (!isLast) {
      const nextIndex = currentStepIndex + 1;
      setCurrentStepIndex(nextIndex);
      const nextTab = TOUR_STEPS[nextIndex].tabId;
      if (nextTab) {
        onNavigateTab(nextTab);
      }
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    if (!isFirst) {
      const prevIndex = currentStepIndex - 1;
      setCurrentStepIndex(prevIndex);
      const prevTab = TOUR_STEPS[prevIndex].tabId;
      if (prevTab) {
        onNavigateTab(prevTab);
      }
    }
  };

  const handleJumpToStep = (index: number) => {
    setCurrentStepIndex(index);
    const targetTab = TOUR_STEPS[index].tabId;
    if (targetTab) {
      onNavigateTab(targetTab);
    }
  };

  const handleComplete = () => {
    if (dontShowAgain) {
      localStorage.setItem("df_tour_seen", "true");
    }
    onClose();
  };

  const handleToggleDontShow = () => {
    const nextVal = !dontShowAgain;
    setDontShowAgain(nextVal);
    if (nextVal) {
      localStorage.setItem("df_tour_seen", "true");
    } else {
      localStorage.removeItem("df_tour_seen");
    }
  };

  if (!isOpen) return null;

  const StepIcon = currentStep.icon;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 backdrop-blur-md transition-all duration-300"
      style={{
        background: "rgba(0, 0, 0, 0.65)",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          handleComplete();
        }
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
        className="relative w-full max-w-2xl rounded-3xl border shadow-2xl overflow-hidden flex flex-col backdrop-blur-2xl"
        style={{
          background: "var(--surface)",
          borderColor: "var(--border)",
          boxShadow: "0 25px 60px -15px rgba(0, 0, 0, 0.4), 0 0 40px var(--glow)",
          color: "var(--txt)",
        }}
      >
        {/* Subtle Ethereal Ambient Glow Header */}
        <div
          className="absolute -top-24 -right-24 w-64 h-64 rounded-full pointer-events-none blur-3xl opacity-25"
          style={{ background: "var(--accent)" }}
        />

        {/* Top Header Strip */}
        <div
          className="px-6 py-4 border-b flex items-center justify-between relative z-10 shrink-0"
          style={{ borderColor: "var(--border)", background: "var(--nav)" }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center border shadow-xs"
              style={{
                background: "var(--glow)",
                borderColor: "var(--accent)",
                color: "var(--accent)",
              }}
            >
              <StepIcon size={16} />
            </div>
            <div>
              <span
                className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border"
                style={{
                  background: "var(--glow)",
                  borderColor: "var(--accent)",
                  color: "var(--accent)",
                }}
              >
                {currentStep.badge}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs font-mono font-semibold" style={{ color: "var(--txt-m)" }}>
              Step {currentStepIndex + 1} of {totalSteps}
            </span>
            <button
              type="button"
              onClick={handleComplete}
              className="w-8 h-8 rounded-xl border flex items-center justify-center hover:opacity-75 transition-opacity cursor-pointer"
              style={{
                background: "var(--card)",
                borderColor: "var(--border)",
                color: "var(--txt-m)",
              }}
              title="Close tour"
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 space-y-6 overflow-y-auto max-h-[75vh] relative z-10">
          {/* Title & Subtitle */}
          <div>
            <h2 className="text-xl sm:text-2xl font-black tracking-tight leading-snug" style={{ color: "var(--txt)" }}>
              {currentStep.title}
            </h2>
            <p className="text-xs sm:text-sm mt-1.5 font-medium leading-relaxed" style={{ color: "var(--accent)" }}>
              {currentStep.subtitle}
            </p>
          </div>

          {/* Description */}
          <p className="text-xs sm:text-sm leading-relaxed" style={{ color: "var(--txt-m)" }}>
            {currentStep.description}
          </p>

          {/* Key Benefits Grid */}
          <div
            className="p-4 rounded-2xl border space-y-2.5"
            style={{
              background: "var(--card)",
              borderColor: "var(--border)",
            }}
          >
            <div className="text-[11px] font-mono font-bold uppercase tracking-wider" style={{ color: "var(--txt)" }}>
              Why you'll love this:
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {currentStep.keyBenefits.map((b, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <CheckCircle2 size={13} className="text-emerald-500 shrink-0 mt-0.5" />
                  <span style={{ color: "var(--txt)" }}>{b}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Friendly Pro Tip Box */}
          <div
            className="p-3.5 rounded-xl border flex items-center gap-3 text-xs"
            style={{
              background: "linear-gradient(90deg, var(--glow), transparent)",
              borderColor: "rgba(255, 67, 16, 0.2)",
            }}
          >
            <div
              className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: "var(--accent)", color: "#ffffff" }}
            >
              <Lightbulb size={13} />
            </div>
            <p className="font-medium leading-relaxed" style={{ color: "var(--txt)" }}>
              <strong className="font-bold">Friendly Tip:</strong> {currentStep.proTip}
            </p>
          </div>

          {/* Live Tab Switch Trigger if on a specific tab step */}
          {currentStep.tabId && (
            <div className="flex items-center justify-between pt-1">
              <span className="text-[11px] font-mono" style={{ color: "var(--txt-m)" }}>
                Currently viewing:{" "}
                <span className="font-bold text-[var(--accent)]">{currentTab.toUpperCase()}</span> tab
              </span>
              <button
                type="button"
                onClick={() => onNavigateTab(currentStep.tabId!)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-transform hover:scale-[1.02] cursor-pointer"
                style={{
                  background: currentTab === currentStep.tabId ? "var(--glow)" : "var(--surface)",
                  borderColor: currentTab === currentStep.tabId ? "var(--accent)" : "var(--border)",
                  color: "var(--accent)",
                }}
              >
                <Play size={11} className="fill-current" />
                <span>{currentStep.tryButtonText || "Show me this tab now"}</span>
              </button>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div
          className="px-6 py-4 border-t flex flex-wrap items-center justify-between gap-3 relative z-10 shrink-0"
          style={{ borderColor: "var(--border)", background: "var(--nav)" }}
        >
          {/* Step Dots & Don't Show Again */}
          <div className="flex items-center gap-4">
            {/* Step indicator dots */}
            <div className="flex items-center gap-1.5">
              {TOUR_STEPS.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleJumpToStep(idx)}
                  className={`h-2 rounded-full transition-all cursor-pointer ${
                    currentStepIndex === idx ? "w-6" : "w-2 hover:opacity-100 opacity-40"
                  }`}
                  style={{
                    background: currentStepIndex === idx ? "var(--accent)" : "var(--txt-m)",
                  }}
                  title={`Go to step ${idx + 1}`}
                />
              ))}
            </div>

            {/* Checkbox */}
            <label className="flex items-center gap-2 text-[11px] cursor-pointer select-none" style={{ color: "var(--txt-m)" }}>
              <input
                type="checkbox"
                checked={dontShowAgain}
                onChange={handleToggleDontShow}
                className="rounded cursor-pointer accent-[var(--accent)]"
              />
              <span>Don't show on start</span>
            </label>
          </div>

          {/* Navigation Action Buttons */}
          <div className="flex items-center gap-2">
            {!isFirst && (
              <button
                type="button"
                onClick={handlePrev}
                className="px-3.5 py-2 rounded-xl text-xs font-bold border flex items-center gap-1.5 transition-opacity hover:opacity-80 cursor-pointer"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              >
                <ArrowLeft size={13} />
                <span>Back</span>
              </button>
            )}

            <button
              type="button"
              onClick={handleNext}
              className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all hover:scale-[1.02] active:scale-95 cursor-pointer shadow-md"
              style={{
                background: "var(--accent)",
                color: "#ffffff",
                boxShadow: "0 0 15px var(--glow)",
              }}
            >
              <span>{isLast ? "Ready! Get Started 🎉" : "Next Step"}</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
