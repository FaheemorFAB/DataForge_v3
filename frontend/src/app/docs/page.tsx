"use client";

import React, { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import Header from "@/app/components/landing/Header";
import Footer from "@/app/components/landing/Footer";
import WorkspaceLaunchModal from "@/app/components/landing/WorkspaceLaunchModal";
import LoginModal from "@/app/components/landing/LoginModal";
import CTABanner from "@/app/components/landing/CTABanner";
import {
  Search,
  BookOpen,
  ArrowRight,
  Database,
  Sparkles,
  Cpu,
  Layers,
  FileSpreadsheet,
  Download,
  ShieldCheck,
  CheckCircle2,
  Users,
  Terminal,
  Code2,
  Bot,
  Zap,
  TrendingUp,
  Sliders,
  Table as TableIcon,
  HelpCircle,
  ExternalLink,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  ChevronUp,
  Building,
  HeartPulse,
  ShoppingBag,
  LineChart,
  Lightbulb,
  Copy,
  Check,
  Play,
  FileText,
  Boxes,
  Compass,
  Menu,
  X,
  Share2,
  BarChart3,
  Presentation,
  ShieldAlert,
  GitBranch,
  Lock,
  Workflow,
  Server,
  Layers2,
} from "lucide-react";

export interface DocArticle {
  id: string;
  category: string;
  categoryTitle: string;
  badge?: string;
  title: string;
  description: string;
  breadcrumb: string;
  icon: any;
  callout?: {
    title: string;
    text: string;
  };
  whatItIs: string;
  howItWorksSteps: {
    step: string;
    title: string;
    detail: string;
    codeSnippet?: string;
    codeLang?: string;
  }[];
  whyUseIt: string[];
  useCases: {
    industry: string;
    title: string;
    description: string;
    icon: any;
  }[];
  codeExample?: {
    filename: string;
    lang: string;
    code: string;
  };
  proTips: string[];
}

export interface NavChildItem {
  id: string;
  title: string;
  badge?: string;
}

export interface NavItem {
  id: string;
  title: string;
  badge?: string;
  children?: NavChildItem[];
}

export interface NavSection {
  id: string;
  title: string;
  icon: any;
  badge?: string;
  subItems?: NavItem[];
}

export default function DocumentationPage() {
  const [activeArticleId, setActiveArticleId] = useState<string>("cleaning-dynamic");
  const [searchQuery, setSearchQuery] = useState("");
  const [copiedCodeKey, setCopiedCodeKey] = useState<string | null>(null);
  const [launchModalOpen, setLaunchModalOpen] = useState(false);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Accordion open/close state for tree navigation
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    "getting-started": true,
    cleaning: true,
    "reports-eda": true,
    ingestion: true,
    joins: false,
    automl: false,
    "ai-analyst": true,
    exports: false,
    governance: false,
  });

  const toggleSection = (sectionId: string) => {
    setOpenSections((prev) => ({
      ...prev,
      [sectionId]: !prev[sectionId],
    }));
  };

  // Prevent body scrolling and handle escape key when mobile sidebar drawer is open
  useEffect(() => {
    if (mobileSidebarOpen) {
      document.body.style.overflow = "hidden";
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === "Escape") setMobileSidebarOpen(false);
      };
      window.addEventListener("keydown", handleKeyDown);
      return () => {
        document.body.style.overflow = "";
        window.removeEventListener("keydown", handleKeyDown);
      };
    } else {
      document.body.style.overflow = "";
    }
  }, [mobileSidebarOpen]);

  // ── DOCUMENTATION ARTICLES (Written in friendly, practical step-by-step English) ──
  const articles: DocArticle[] = [
    // ── 1. GETTING STARTED ──────────────────────────────────────────────────
    {
      id: "quickstart",
      category: "getting-started",
      categoryTitle: "Getting Started",
      badge: "START HERE",
      title: "Quickstart Guide",
      description: "How to import, clean, visualize, and train predictive models in DataForge in under two minutes.",
      breadcrumb: "Getting Started > Quickstart",
      icon: Compass,
      callout: {
        title: "No Setup or Installations Needed",
        text: "You do not need to install Python, configure virtual environments, or run terminal commands. DataForge runs directly inside your web browser connected to our high-speed analytical engine.",
      },
      whatItIs:
        "DataForge is a simple, all-in-one data workspace built for anyone who works with spreadsheets. If you have ever experienced Excel freezing on a large file, struggled with messy columns, or wished you could build machine learning predictions without writing code, DataForge was made for you. In under two minutes, you can upload your data, clean up errors with one click, explore interactive graphs, and get executive business reports.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Upload or Connect Your File",
          detail: "Open the Ingestion tab and drop in any CSV, Excel spreadsheet, or paste a link to a Google Sheet. DataForge reads your headers, figures out your data types, and shows an instant table preview with row counts and health metrics.",
        },
        {
          step: "02",
          title: "Clean Messy Data in One Click",
          detail: "Switch to the Cleaner tab. Click the 'Auto-Clean' button to automatically fill empty cells, cap extreme typos, and strip duplicates. If you want custom control, use Dynamic Cleaning to pick rules column-by-column.",
        },
        {
          step: "03",
          title: "Explore Charts and Distributions",
          detail: "Open the EDA and Visual Chart Studio tabs to see automated summary cards, correlation heatmaps, and customizable Bar, Line, or Scatter plots with instant hover tooltips.",
        },
        {
          step: "04",
          title: "Train AI Models & Export",
          detail: "Head to the AutoML tab, select what you want to predict (like Customer Churn or Sales), and click 'Run Tournament'. DataForge benchmarks top algorithms, crowns a champion, and lets you download clean data or production code.",
        },
      ],
      whyUseIt: [
        "Takes the frustration out of messy spreadsheets without requiring complex formulas or coding.",
        "Handles large datasets with up to 1,000,000 rows smoothly without freezing your computer.",
        "Safe and reversible: your raw data is always preserved, and you can undo changes anytime.",
      ],
      useCases: [
        {
          industry: "Retail & E-Commerce",
          title: "Daily Store Sales & Inventory",
          description: "Combine daily order spreadsheets from multiple stores, fix missing customer IDs, and forecast next week's inventory demand.",
          icon: ShoppingBag,
        },
        {
          industry: "Business Operations",
          title: "Customer Contact Audits",
          description: "Deduplicate lead lists, standardize city and department names, and find high-value customer segments.",
          icon: Users,
        },
      ],
      proTips: [
        "Click 'Try with Sample Dataset' inside the workspace if you want to explore all features before uploading your own file.",
        "You can toggle between Dark and Light mode anytime from the top navigation bar to suit your eyes.",
      ],
    },
    {
      id: "architecture",
      category: "getting-started",
      categoryTitle: "Getting Started",
      badge: "ENGINE SPEED",
      title: "How DataForge Runs Fast (DuckDB & Parquet)",
      description: "How our lightweight columnar engine processes millions of rows smoothly without crashing your browser.",
      breadcrumb: "Getting Started > Architecture",
      icon: Server,
      callout: {
        title: "Why It Never Freezes Your Computer",
        text: "Standard spreadsheet apps try to hold every cell of a giant file in your computer's RAM. DataForge uses DuckDB's columnar technology, reading only the exact columns you need so your computer stays fast, cool, and responsive.",
      },
      whatItIs:
        "Have you ever opened a large CSV or Excel file only to watch your computer slow down to a crawl or show a spinning wheel? Traditional programs load the entire uncompressed file into memory all at once. DataForge is built on modern columnar technology using DuckDB and Apache Parquet. Instead of reading whole rows from start to finish, it organizes data into lightweight columns and streams only what you are viewing on screen.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Smart Column Snapshots",
          detail: "When you upload a file, DataForge creates a fast, compressed snapshot in Parquet format. This protects your original file from being accidentally altered and makes future loading up to 5x faster.",
        },
        {
          step: "02",
          title: "In-Memory Columnar Speed",
          detail: "When you filter, sort, or join data, DuckDB executes the math directly in your computer's high-speed memory, crunching thousands of numbers at once in milliseconds.",
        },
        {
          step: "03",
          title: "Safe Sandboxed Workspace",
          detail: "When you run cleaning rules or ask our AI questions, the calculations run in an isolated environment with strict limits to keep your data secure and private.",
        },
      ],
      whyUseIt: [
        "Query and filter large spreadsheets containing hundreds of thousands of rows with instant sub-second responses.",
        "Zero spreadsheet crashes: no more lost work or 'application not responding' alerts.",
        "Your original uploaded files remain 100% safe, immutable, and untouched.",
      ],
      useCases: [
        {
          industry: "Product & Web Analytics",
          title: "High-Volume Event Logs",
          description: "Filter and explore 500,000+ app clickstream events without lag or waiting.",
          icon: Cpu,
        },
        {
          industry: "Financial Operations",
          title: "Transaction Ledger Audits",
          description: "Calculate sums and running balances across multi-year bank statements instantly.",
          icon: LineChart,
        },
      ],
      proTips: [
        "Uploading files in Parquet format instead of CSV gives you 5x faster uploads because Parquet is pre-compressed and typed.",
      ],
    },

    // ── 2. DATA CLEANING ENGINE ─────────────────────────────────────────────
    {
      id: "cleaning-auto",
      category: "cleaning",
      categoryTitle: "Data Cleaning Engine",
      badge: "1-CLICK FIX",
      title: "1-Click Auto Cleaning",
      description: "Fix missing values, cap extreme outlier typos, and remove duplicate rows with a single click.",
      breadcrumb: "Data Cleaning > 1-Click Auto Cleaning",
      icon: Sparkles,
      callout: {
        title: "Completely Safe & Reversible",
        text: "Auto-Clean never overwrites your original uploaded data. It creates a brand-new clean snapshot, and you can revert back to your raw data with a single click at any time.",
      },
      whatItIs:
        "1-Click Auto Cleaning is our automated data hygiene tool designed to turn messy spreadsheets into clean, reliable tables instantly. In the real world, data is full of empty blank cells, impossible typos (like an age of 999), and duplicate rows from repeated form submissions. Instead of spending hours hunting down errors by hand, one click on 'Auto-Clean' analyzes every column, repairs missing numbers using smart medians, caps extreme spikes, and cleans up duplicates.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Click 'Auto-Clean' in the Cleaner Tab",
          detail: "Navigate to the Cleaner tab and click the prominent 'Auto-Clean' button. DataForge immediately starts the automated 4-step cleanup.",
        },
        {
          step: "02",
          title: "Smart Median & Mode Imputation",
          detail: "Empty numeric cells are filled with the column's Median (the middle value, so extreme numbers don't distort the average). Empty text cells are filled with 'Unknown' so charts don't break.",
        },
        {
          step: "03",
          title: "Caps Extreme Outlier Typos",
          detail: "The engine uses statistical fences (Interquartile Range) to find impossible numbers and gently caps them to the boundary. This keeps the row useful without letting a typo ruin your charts.",
        },
        {
          step: "04",
          title: "Removes Duplicates and Extra Spaces",
          detail: "Strips accidental leading and trailing spaces from text (like ' New York ' vs 'New York') and drops exact duplicate rows.",
        },
      ],
      whyUseIt: [
        "Saves 30 to 60 minutes of tedious manual copy-pasting and formula writing on every new spreadsheet.",
        "Prevents broken charts and '#VALUE!' errors caused by missing cells.",
        "Automatically generates a clean Python script so you can repeat the exact same cleanup in the future.",
      ],
      useCases: [
        {
          industry: "Healthcare & Clinics",
          title: "Patient Visit Normalization",
          description: "Clean medical visit records, fill missing test values with group medians, and remove duplicate check-in entries.",
          icon: HeartPulse,
        },
        {
          industry: "Marketing Teams",
          title: "Event Lead List Cleaning",
          description: "Trim trailing spaces from emails, standardize capitalization, and remove duplicate registrations.",
          icon: Users,
        },
      ],
      codeExample: {
        filename: "auto_clean_pipeline.py",
        lang: "python",
        code: `# DataForge 1-Click Auto-Clean Pipeline
import pandas as pd
import numpy as np

def run_auto_clean(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Drop exact duplicate rows
    df = df.drop_duplicates()
    
    # 2. Impute numerics using statistical median
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].median())
        
        # 3. Cap extreme outliers using IQR fences
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        df[col] = df[col].clip(q1 - 1.5 * iqr, q3 + 1.5 * iqr)
        
    return df`,
      },
      proTips: [
        "Check the Data Health card after running Auto-Clean to see the exact percentage of missing values that were repaired.",
        "If you only want to clean specific columns, switch to the 'Dynamic Cleaning' mode right next to the Auto-Clean button.",
      ],
    },
    {
      id: "cleaning-dynamic",
      category: "cleaning",
      categoryTitle: "Data Cleaning Engine",
      badge: "CUSTOM RULES",
      title: "Dynamic Interactive Cleaning",
      description: "Choose custom rules per column, preview the live before-and-after diff, and apply changes with confidence.",
      breadcrumb: "Data Cleaning > Dynamic Interactive Cleaning",
      icon: Sliders,
      callout: {
        title: "Live Before-and-After Diff Preview",
        text: "Never guess what a rule will do. DataForge shows you an interactive side-by-side diff comparing your original data against the clean version before you commit any changes.",
      },
      whatItIs:
        "Dynamic Interactive Cleaning gives you complete, surgical control over your data. Rather than applying a blanket rule to everything, you choose the exact column you want to fix and pick the rule that fits your business logic. Want to replace missing discounts with 0, change customer names to UPPERCASE, mask phone numbers for privacy, or filter out negative prices? Dynamic Cleaning lets you set the rule, inspect a live before-and-after preview, and apply it with confidence.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Select Your Column",
          detail: "Pick one or more columns from the list. You can use the search bar or type filters (numeric, text, datetime, missing) to find columns quickly.",
        },
        {
          step: "02",
          title: "Choose an Action Category",
          detail: "Select from Impute (fill blanks with median, mean, mode, or custom value), Outlier (clip or drop extreme spikes), Scale, Encode, Text/PII (trim, casing, regex, phone/email masking), or Type Cast.",
        },
        {
          step: "03",
          title: "Click 'Preview Diff'",
          detail: "DataForge runs a fast preview comparing your current values with the proposed changes, showing exact numbers and row counts before anything touches your dataset.",
        },
        {
          step: "04",
          title: "Click 'Apply Rule'",
          detail: "When you're happy with the preview, click 'Apply Rule'. DataForge applies the change, adds it to your recipe history, and updates your table immediately.",
        },
      ],
      whyUseIt: [
        "Zero guesswork: you see exactly what will happen to your data before committing any change.",
        "Full control: customize cleaning rules to match your specific business requirements.",
        "Unlimited undo: step backward through your rule history anytime if you change your mind.",
      ],
      useCases: [
        {
          industry: "Retail Catalog Management",
          title: "Product SKU & Price Normalization",
          description: "Force SKU strings to uppercase, strip currency symbols, and ensure discount percentages stay between 0% and 100%.",
          icon: ShoppingBag,
        },
        {
          industry: "Human Resources",
          title: "Employee Compensation Formatting",
          description: "Standardize department names ('sales' vs 'Sales') and impute missing bonus figures with a custom zero value.",
          icon: Users,
        },
      ],
      proTips: [
        "Always click 'Preview Diff' before using rules that drop rows so you don't accidentally remove valuable customer records.",
        "Use the PII Masking option under Text to automatically hide phone numbers, emails, and credit cards before sharing datasets with your team.",
      ],
    },
    {
      id: "cleaning-diff",
      category: "cleaning",
      categoryTitle: "Data Cleaning Engine",
      badge: "CODE EXPORT",
      title: "Diff Engine & Python Script Export",
      description: "Inspect mathematical before-and-after differences and download your cleaning steps as a ready-to-run Python script.",
      breadcrumb: "Data Cleaning > Diff & Script Export",
      icon: GitBranch,
      callout: {
        title: "Zero Vendor Lock-In",
        text: "The exported Python script uses standard open-source libraries (Pandas and NumPy). You can run it on your laptop, in a Jupyter notebook, or in your company's production pipelines without needing DataForge installed.",
      },
      whatItIs:
        "The Diff Engine and Script Export feature connects visual data cleaning with real-world programming. While you click and clean visually in your browser, DataForge silently tracks every mathematical adjustment. At any time, you can view the exact before-and-after metrics (how missing values dropped and how averages shifted) and download a clean, standalone Python script that reproduces the identical cleaning steps on any computer.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Calculates Live Differences",
          detail: "Whenever you preview or apply a cleaning rule, the engine calculates the net change in missing cells, average values, and row counts.",
        },
        {
          step: "02",
          title: "Automated Python Code Generation",
          detail: "DataForge translates your visual clicks into clean, commented Python code using standard Pandas and NumPy functions.",
        },
        {
          step: "03",
          title: "Download or Copy with 1 Click",
          detail: "Click 'Export Cleaning Script' to view the code modal, copy it to your clipboard, or download dataforge_clean.py.",
        },
        {
          step: "04",
          title: "Run in Any Pipeline",
          detail: "Hand the script to your engineering team, run it in scheduled jobs (like Apache Airflow or cron), or commit it to your team's Git repository.",
        },
      ],
      whyUseIt: [
        "No need to manually translate visual clicks into Python code for your software developers.",
        "Guarantees that your automated backend pipelines clean data the exact same way you verified visually.",
        "Includes helpful docstrings and comments explaining each transformation step clearly.",
      ],
      useCases: [
        {
          industry: "Data Engineering",
          title: "Automated Nightly Batch Cleaning",
          description: "Plug the exported Python script into an automated pipeline to clean daily spreadsheet drops.",
          icon: Terminal,
        },
        {
          industry: "Academic & Compliance Audits",
          title: "Reproducible Research",
          description: "Attach the generated Python script to your report so reviewers can verify every cleaning step.",
          icon: ShieldCheck,
        },
      ],
      proTips: [
        "Teammates can review the exported Python script during pull requests to verify that business cleaning rules match company standards.",
      ],
    },

    // ── 3. EXPLORATORY DATA ANALYSIS & REPORTS ──────────────────────────────
    {
      id: "eda-statistical",
      category: "reports-eda",
      categoryTitle: "Exploratory Data Analysis",
      badge: "COMPLETE EDA",
      title: "Statistical Profile (Full Dataset)",
      description: "Deep statistical distributions, quantile metrics, and correlation heatmaps across every single row.",
      breadcrumb: "EDA & Reports > Statistical Profile",
      icon: BarChart3,
      callout: {
        title: "100% Full Dataset Analysis",
        text: "DataForge analyzes all your rows without downsampling or skipping data. You will never miss subtle outliers, rare categories, or quiet anomalies that sample limits hide.",
      },
      whatItIs:
        "The Statistical Profile is a thorough, 360-degree health checkup for your entire dataset. Instead of writing dozens of lines of Python code or creating pivot tables by hand, DataForge calculates everything for you: distribution shapes, averages, medians, 25th and 75th percentiles, extreme values, missing value counts, and correlation heatmaps showing which columns move together.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Click 'Generate Statistical Profile'",
          detail: "In the Exploratory Data Analysis (EDA) tab, click 'Generate Statistical Profile'. The engine processes every row across your entire table in the background.",
        },
        {
          step: "02",
          title: "Explore Interactive Summaries",
          detail: "View detailed cards for each column showing its minimum, maximum, mean, median, missing count, and unique values.",
        },
        {
          step: "03",
          title: "Check Correlation Heatmaps",
          detail: "Inspect the color-coded correlation matrix to see which columns have strong positive relationships (rising together) or negative relationships.",
        },
        {
          step: "04",
          title: "Review Data Quality Warnings",
          detail: "The profile highlights high cardinality warnings, zero-value columns, and highly correlated pairs so you can prepare your data properly.",
        },
      ],
      whyUseIt: [
        "Instantly spot data skewness, missing value hotspots, and duplicate keys in seconds.",
        "Saves hours of writing repetitive Matplotlib, Seaborn, or Excel charting formulas.",
        "Helps you discover hidden relationships between columns before building machine learning models.",
      ],
      useCases: [
        {
          industry: "Product Growth",
          title: "User Engagement Skewness",
          description: "Discover whether 5% of power users account for 80% of total app usage time.",
          icon: Users,
        },
        {
          industry: "Financial Risk",
          title: "Loan Application Audits",
          description: "Spot unusual clusters of debt-to-income ratios and locate missing income entries.",
          icon: LineChart,
        },
      ],
      proTips: [
        "If two columns have a correlation score above 0.85, they are providing almost identical information—consider dropping one before running machine learning to keep your models simple and accurate.",
      ],
    },
    {
      id: "eda-biz-report",
      category: "reports-eda",
      categoryTitle: "Exploratory Data Analysis",
      badge: "EXECUTIVE BRIEFING",
      title: "AI Business Analyst Report",
      description: "An AI-generated narrative that explains key business drivers, highlights risks, and prepares a printable executive PDF.",
      breadcrumb: "EDA & Reports > AI Business Report",
      icon: FileText,
      callout: {
        title: "One-Click Printable PDF",
        text: "The executive report includes a 'Download PDF' button that opens your browser's print dialog pre-formatted for crisp, clean executive reading.",
      },
      whatItIs:
        "The AI Business Analyst Report bridges the gap between raw numbers and executive decisions. Non-technical bosses and clients don't want to dig through thousand-row spreadsheets—they want to know what the numbers mean for the business. DataForge uses advanced analytical intelligence (powered by Google Gemini) to read your metrics, detect revenue drivers, identify margin risks, and summarize key takeaways in a clear, boardroom-ready narrative.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Click 'Generate AI Executive Report'",
          detail: "In the EDA tab, switch to the Business Report view and click the generate button. The engine reviews your metrics and key drivers.",
        },
        {
          step: "02",
          title: "Read the Executive Summary",
          detail: "The report delivers a clean briefing covering high-level takeaways, KPI health scorecards, anomaly alerts, and strategic next steps.",
        },
        {
          step: "03",
          title: "Inspect Embedded Charts",
          detail: "Vector charts and distribution graphs are embedded directly into the report, keeping visuals crisp when zoomed in or printed.",
        },
        {
          step: "04",
          title: "Print or Save as PDF",
          detail: "Click 'Download PDF' to open the print dialog and save a clean PDF ready to email to leadership or bring to meetings.",
        },
      ],
      whyUseIt: [
        "Produces professional executive briefings in seconds instead of spending hours hand-writing slides.",
        "Translates raw numbers into plain-English strategic recommendations anyone can understand.",
        "Ready for leadership: includes KPI scorecards, risk alerts, and clear action items.",
      ],
      useCases: [
        {
          industry: "Management Consulting",
          title: "Client Deliverables",
          description: "Generate structured summaries to present to client stakeholders at project milestones.",
          icon: Building,
        },
        {
          industry: "Startup Founders",
          title: "Monthly Investor Updates",
          description: "Summarize revenue growth, customer acquisition costs, and churn drivers in a polished memo.",
          icon: LineChart,
        },
      ],
      proTips: [
        "Click 'Download PDF' and choose 'Save as PDF' to generate a file you can immediately attach to your stakeholder update emails.",
      ],
    },
    {
      id: "eda-deck",
      category: "reports-eda",
      categoryTitle: "Exploratory Data Analysis",
      badge: "5-SLIDE DECK",
      title: "5-Slide Executive Presentation Deck",
      description: "A dedicated landscape presentation deck with clean slide pagination and zero page overlap when printing.",
      breadcrumb: "EDA & Reports > 5-Slide Presentation Deck",
      icon: Presentation,
      callout: {
        title: "Clean Print Pagination",
        text: "Dedicated landscape print styles enforce exactly one slide per page. When printing or exporting to PDF, each slide sits cleanly on its own sheet with zero visual bleed-through.",
      },
      whatItIs:
        "The 5-Slide Presentation Deck turns your data into five beautifully formatted executive presentation slides: 1) Executive Health Scorecard, 2) Dimensional Scale & Volume, 3) Distribution Drivers & Variance, 4) Metric Correlations, and 5) Strategic Recommendations. Built specifically for landscape viewing and PDF printing, it gives you a presentation you can present live or print as physical handouts.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Browse the 5 Slides",
          detail: "In the EDA tab, open the Presentation Deck view and use the Next and Previous arrow buttons to review each slide.",
        },
        {
          step: "02",
          title: "Slide 1 to 5 Structure",
          detail: "Review overall health scores on Slide 1, dataset scale on Slide 2, top driver distributions on Slide 3, correlation matrix on Slide 4, and priority action items on Slide 5.",
        },
        {
          step: "03",
          title: "Click 'Print Deck (5 Slides)'",
          detail: "DataForge isolates the presentation view and launches your browser's print dialog.",
        },
        {
          step: "04",
          title: "Export Clean Landscape PDF",
          detail: "Choose 'Landscape' orientation. The built-in CSS rules ensure each slide prints onto its own dedicated page without overflowing.",
        },
      ],
      whyUseIt: [
        "Zero slide overlap: every slide prints neatly on its own sheet with crisp borders.",
        "Instant presentations: no need to spend hours copying charts into PowerPoint or Google Slides.",
        "Perfect for board meetings, client review packets, and project archives.",
      ],
      useCases: [
        {
          industry: "Corporate Strategy",
          title: "Board of Directors Handout",
          description: "Print a 5-page landscape packet for directors to review during quarterly meetings.",
          icon: Building,
        },
        {
          industry: "Project Reviews",
          title: "Sprint Milestone Summary",
          description: "Showcase data quality, key metrics, and next steps to cross-functional teams.",
          icon: LineChart,
        },
      ],
      proTips: [
        "In your browser print settings, make sure 'Background graphics' is checked so that card colors and metric badges print vibrantly.",
      ],
    },
    {
      id: "eda-charts",
      category: "reports-eda",
      categoryTitle: "Exploratory Data Analysis",
      badge: "INTERACTIVE CHARTS",
      title: "Visual Chart Studio",
      description: "Build Bar, Line, Scatter, Pie, Box, and Funnel charts with hover tooltips and customizable color palettes.",
      breadcrumb: "EDA & Reports > Chart Studio",
      icon: LineChart,
      callout: {
        title: "Interactive & Multi-Dimensional",
        text: "Hover over any data point to see exact numbers, zoom in on dense regions, switch color themes, and export high-resolution chart images with one click.",
      },
      whatItIs:
        "The Visual Chart Studio is your hands-on graphing canvas. You don't need to know Python plotting libraries or complicated spreadsheet chart wizards. Simply pick which column goes on the horizontal X-axis and which goes on the vertical Y-axis, select your chart style (Bar, Line, Scatter, Pie, Box Plot, Waterfall, etc.), pick a vibrant color theme, and your graph renders instantly.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Choose X and Y Columns",
          detail: "Select the columns you want to visualize from simple dropdown menus. DataForge automatically recognizes dates, categories, and numbers.",
        },
        {
          step: "02",
          title: "Select Your Chart Type",
          detail: "Pick from 12 versatile chart styles: Bar (for categories), Line (for trends over time), Scatter (for relationships), Box Plot (for distributions), Pie/Donut, or Waterfall.",
        },
        {
          step: "03",
          title: "Pick a Visual Color Palette",
          detail: "Switch between curated palettes like Neon Indigo, Sapphire Corporate, Emerald Forest, Cyberpunk, or Slate to match your brand.",
        },
        {
          step: "04",
          title: "Download or Pin to Dashboard",
          detail: "Hover over points to see exact numbers, or click the download icon to save a high-resolution PNG image for your documents.",
        },
      ],
      whyUseIt: [
        "Answers visual questions instantly without writing code in Python or R.",
        "Interactive tooltips let you inspect individual values and outliers effortlessly.",
        "Clean, modern design aesthetics make your charts look polished and professional.",
      ],
      useCases: [
        {
          industry: "Marketing Campaigns",
          title: "Conversion Rate Trends",
          description: "Plot monthly conversion rates over time against ad spend to find the most profitable channels.",
          icon: ShoppingBag,
        },
        {
          industry: "Sales Leadership",
          title: "Regional Revenue Breakdown",
          description: "Use Bar and Pie charts to compare quarterly sales across geographic territories.",
          icon: LineChart,
        },
      ],
      proTips: [
        "Use Scatter plots when you want to compare two numeric metrics (like Price vs. Quantity Sold) to spot customer clusters or unusual outliers.",
      ],
    },

    // ── 4. DATA INGESTION HUB ───────────────────────────────────────────────
    {
      id: "ingestion-local",
      category: "ingestion",
      categoryTitle: "Data Ingestion Hub",
      badge: "DRAG & DROP",
      title: "Local File Ingestion (CSV, Excel, Parquet)",
      description: "Drag and drop any spreadsheet with automatic delimiter detection, encoding support, and instant previews.",
      breadcrumb: "Ingestion > Local Files",
      icon: Database,
      callout: {
        title: "Never Freezes on Large Files",
        text: "While traditional desktop software freezes when opening massive CSV files, DataForge easily handles files with up to 1,000,000 rows without lag.",
      },
      whatItIs:
        "Local File Ingestion is the quick front door to DataForge. Just drag and drop any spreadsheet or data file from your computer. You don't have to worry about whether your CSV uses commas, semicolons, or tabs, or whether it has special characters. DataForge figures out the format automatically, reads your column headers, and shows you an instant table preview with health scores in seconds.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Drag and Drop Your File",
          detail: "Drag any CSV, Excel (.xlsx, .xls), TSV, Parquet, or JSON file into the upload dropzone.",
        },
        {
          step: "02",
          title: "Automatic Delimiter & Encoding Detection",
          detail: "DataForge samples the file to determine whether commas, semicolons, or tabs were used, and handles international character encodings (UTF-8, Latin-1) smoothly.",
        },
        {
          step: "03",
          title: "Instant Parquet Conversion",
          detail: "The file is converted into an in-memory columnar snapshot, giving you instant table pagination and search.",
        },
        {
          step: "04",
          title: "Review Data Health",
          detail: "Check the initial preview to see total rows, columns, detected data types, and initial missing cell counts.",
        },
      ],
      whyUseIt: [
        "Never crashes on unusual delimiters or international accents.",
        "Preserves your original file safely without ever modifying or overwriting it.",
        "Handles large spreadsheets that cause desktop programs to freeze.",
      ],
      useCases: [
        {
          industry: "Finance",
          title: "Quarterly Ledger Uploads",
          description: "Upload 500,000-row ledger exports and search transactions without waiting.",
          icon: LineChart,
        },
        {
          industry: "Logistics",
          title: "Shipping Manifest Ingestion",
          description: "Drop in daily Excel shipping manifests to audit delivery timestamps.",
          icon: ShoppingBag,
        },
      ],
      proTips: [
        "If you have a very large file, saving it as Parquet format uploads 5x faster because Parquet is pre-compressed.",
      ],
    },
    {
      id: "ingestion-sheets",
      category: "ingestion",
      categoryTitle: "Data Ingestion Hub",
      badge: "LIVE CLOUD SYNC",
      title: "Cloud Google Sheets & Excel Online",
      description: "Connect live Google Sheets and Microsoft 365 Excel Online workbooks with automatic tab scanning and live 1-click delta synchronization.",
      breadcrumb: "Ingestion > Cloud Sheets",
      icon: FileSpreadsheet,
      callout: {
        title: "Intelligent Delta Synchronization & Tab Scanning",
        text: "When your team updates numbers in Google Sheets or OneDrive Excel Online, click 'Sync Sheet' in your workspace header. DataForge calculates the exact change delta (+X rows, +Y cols) and prompts you with a visual summary modal.",
      },
      whatItIs:
        "Cloud Sheets ingestion connects Google Sheets and Microsoft 365 (OneDrive / SharePoint) Excel Online workbooks directly to DataForge using standard shared links. Instead of manually downloading CSV files every day, you link the cloud workbook once. DataForge automatically scans all worksheets in the workbook, allowing you to select any tab with one click. When colleagues make updates, the 'Sync Sheet' button in the workspace Explorer and header fetches changes, runs delta verification, and updates your active analysis in place.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Copy Workbook Sharing Link",
          detail: "In Google Sheets or Excel Online, set sharing to 'Anyone with the link can view' (or generate a shared OneDrive link) and paste the URL into DataForge.",
        },
        {
          step: "02",
          title: "Scan & Select Workbook Tabs",
          detail: "Click the 'Tabs' button to automatically probe the workbook structure. Select your target worksheet from the detected tab list.",
        },
        {
          step: "03",
          title: "High-Speed Ingestion & Typing",
          detail: "DataForge streams the worksheet rows into memory, validates column headers, infers optimal data types, and generates an instant preview profile.",
        },
        {
          step: "04",
          title: "1-Click 'Sync Sheet' with Delta Detection",
          detail: "Click 'Sync Sheet' in the workspace toolbar whenever new rows are added. DataForge inspects before/after shapes, reports exact additions (e.g. '+45 rows, +2 columns'), and synchronizes your tables automatically.",
          codeSnippet: "# Live synchronization endpoint\nPOST /api/workspace/sync-sheets\nPayload: { upload_id: '...', source_config: { url: 'https://docs.google.com/spreadsheets/...' } }\nResponse: { ok: true, changed: true, delta: { rows_added: 45, cols_added: 2 } }",
          codeLang: "bash",
        },
      ],
      whyUseIt: [
        "Works seamlessly across both Google Sheets and Microsoft 365 OneDrive / SharePoint Excel Online.",
        "Automatic tab detection lets you pick specific worksheets without opening external programs.",
        "Live 'Sync Sheet' delta popup shows exactly what changed (+X rows, +Y cols) or confirms 'Already in Sync'.",
        "Zero API keys, service account credentials, or OAuth setup required for public or organization links.",
      ],
      useCases: [
        {
          industry: "Operations & Logistics",
          title: "Live Shipping Manifest Audits",
          description: "Connect dispatch Google Sheets and refresh shipping logs every morning with 1 click.",
          icon: ShoppingBag,
        },
        {
          industry: "Marketing & Growth",
          title: "Multi-Tab Campaign Tracking",
          description: "Scan multi-tab Excel Online workbooks to ingest regional advertising spend sheets.",
          icon: LineChart,
        },
      ],
      proTips: [
        "If your spreadsheet has multiple tabs (e.g. 'January', 'February', 'Summary'), click the 'Tabs' button to switch between them instantly.",
        "When 'Sync Sheet' runs, DataForge safely updates your active DataFrame while preserving any saved clean snapshots for instant rollback.",
      ],
    },
    {
      id: "ingestion-vault",
      category: "ingestion",
      categoryTitle: "Data Ingestion Hub",
      badge: "ENCRYPTED CONNECTIONS",
      title: "Database Connection Vault",
      description: "Secure credential storage to pull tables from PostgreSQL, MySQL, Supabase, ClickHouse, SQLite, and DuckDB databases safely.",
      breadcrumb: "Ingestion > Database Vault",
      icon: Lock,
      callout: {
        title: "Broad Database Support with Zero-Knowledge Protection",
        text: "Supports cloud services (AWS RDS, PlanetScale, Supabase, ClickHouse Cloud) and local instances (127.0.0.1:3306) with pure-Python drivers and dialect-safe quoting.",
      },
      whatItIs:
        "The Database Connection Vault is an encrypted credential locker that allows your team to securely connect relational databases and data warehouses directly into DataForge. Supporting PostgreSQL, MySQL (via pure-Python PyMySQL), Supabase, ClickHouse Cloud, SQLite, and DuckDB, the Vault eliminates risky password sharing over chat or email. Team members can test connections instantly with the 'Ping' tool, automatically discover database tables, and stream tables or custom SQL queries directly into high-speed memory.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Enter Database Connection URI",
          detail: "Paste your connection URI (e.g. mysql://root:pass@127.0.0.1:3306/mydb or postgresql://user:pass@db.supabase.co:5432/postgres).",
        },
        {
          step: "02",
          title: "Instant 'Ping' Connectivity Test",
          detail: "Click 'Ping' to verify network reachability, validate SSL/TLS handshakes, and verify authentication credentials before loading data.",
          codeSnippet: "# Database connection test\nPOST /api/upload/database/test\nPayload: { connection_string: 'mysql://root:pass@127.0.0.1:3306/sales_db' }\nResponse: { ok: true, message: 'Connection successful' }",
          codeLang: "bash",
        },
        {
          step: "03",
          title: "Automatic Table Discovery",
          detail: "Upon successful ping, DataForge inspects the database schema and populates the Target Table dropdown with all available tables.",
        },
        {
          step: "04",
          title: "Stream Rows with Dialect-Safe Quoting",
          detail: "DataForge queries the selected table using dialect-aware quoting (backticks for MySQL, double quotes for PostgreSQL) to prevent syntax errors and loads the data into an in-memory DuckDB table.",
        },
      ],
      whyUseIt: [
        "Native pure-Python MySQL and ClickHouse drivers guarantee zero missing C-compiler errors on Windows, macOS, or Linux.",
        "SSRF and private IP safeguards protect internal networks while permitting authorized local database development.",
        "Automatic table listing and row previews prevent blind querying mistakes.",
        "Preserves production database stability with pre-ping health checks and query timeout limits.",
      ],
      useCases: [
        {
          industry: "FinTech & Payments",
          title: "Transactional Fraud Audits",
          description: "Connect to a PostgreSQL or Supabase read-replica to audit high-value transaction tables.",
          icon: ShieldCheck,
        },
        {
          industry: "E-Commerce",
          title: "Local & Cloud MySQL Analytics",
          description: "Connect local MySQL instances (127.0.0.1) or cloud AWS RDS databases to analyze customer orders.",
          icon: ShoppingBag,
        },
      ],
      proTips: [
        "Use read-only database credentials when connecting to production databases to guarantee data safety.",
        "When connecting to cloud databases like Supabase or Neon, DataForge automatically appends sslmode=require for secure TLS connections.",
      ],
    },

    // ── 5. RELATIONAL JOIN STUDIO ───────────────────────────────────────────
    {
      id: "joins-canvas",
      category: "joins",
      categoryTitle: "Relational Join Studio",
      badge: "VISUAL BUILDER",
      title: "Visual Join Canvas",
      description: "Combine multiple tables with drag-and-drop connections, automatic key suggestions, and match-rate previews.",
      breadcrumb: "Relational Joins > Visual Canvas",
      icon: Layers,
      callout: {
        title: "Smarter than VLOOKUP, Simpler than SQL",
        text: "No broken #N/A formula errors and no complicated SQL syntax. The Visual Canvas suggests matching columns automatically and previews the joined rows before saving.",
      },
      whatItIs:
        "The Visual Join Canvas lets you combine two or more tables into a single master dataset using a shared column (like Customer ID, Order Number, or Product SKU). If you've ever spent hours wrestling with broken Excel VLOOKUP or XLOOKUP formulas across huge files, the Join Canvas will feel like a breath of fresh air. You pick your tables, see automatic matching recommendations, choose your join strategy, and preview the combined result.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Pick Primary and Secondary Tables",
          detail: "Select your primary dataset (like Orders) and choose a secondary table from your workspace (like Customers).",
        },
        {
          step: "02",
          title: "Automatic Key Recommendations",
          detail: "DataForge scans column names and values to suggest matching keys (e.g. customer_id matching user_id).",
        },
        {
          step: "03",
          title: "Choose Your Join Strategy",
          detail: "Pick your join type: Left Join (keep all primary rows + matching details), Inner Join (only rows that match in both), Right Join, Full Outer, Semi Join, or Anti Join.",
        },
        {
          step: "04",
          title: "Preview and Save",
          detail: "Inspect the live preview table, check the match percentage to make sure no rows were lost, and click 'Execute Join' to save the combined table.",
        },
      ],
      whyUseIt: [
        "Eliminates formula errors, broken references, and memory crashes caused by Excel VLOOKUP on large files.",
        "Automatic key matching spots relationships between columns even if headers have slightly different names.",
        "Shows you exactly which rows matched and which didn't before you finalize the merge.",
      ],
      useCases: [
        {
          industry: "Sales & Marketing",
          title: "Lead Attribution Merging",
          description: "Combine web marketing signups with CRM closed deals to see which ad campaigns generated revenue.",
          icon: Users,
        },
        {
          industry: "Supply Chain",
          title: "Order & Inventory Matching",
          description: "Merge daily sales orders with warehouse product inventories to identify low-stock items.",
          icon: ShoppingBag,
        },
      ],
      proTips: [
        "Use Left Join whenever you want to guarantee that not a single record from your primary table is dropped, even if a customer detail is missing.",
      ],
    },
    {
      id: "joins-engine",
      category: "joins",
      categoryTitle: "Relational Join Studio",
      badge: "LIGHTNING SPEED",
      title: "DuckDB In-Memory Merging",
      description: "High-speed vectorized join execution capable of merging 500,000+ rows in milliseconds.",
      breadcrumb: "Relational Joins > In-Memory Engine",
      icon: Zap,
      callout: {
        title: "Sub-Second Multi-Table Merges",
        text: "By running in-memory hash joins directly on columnar vectors, DataForge combines huge tables up to 20x faster than standard Python Pandas or desktop spreadsheet tools.",
      },
      whatItIs:
        "Under the hood, the Join Canvas is powered by DuckDB's in-memory analytical join engine. Traditional tools slow down when joining large tables because they compare rows one-by-one or create massive temporary files on your hard drive. DuckDB creates an ultra-fast hash index on your matching keys in memory, pairing up records across columns simultaneously in a fraction of a second.",
      howItWorksSteps: [
        {
          step: "01",
          title: "High-Speed Hash Indexing",
          detail: "DuckDB builds a lightweight hash index on the join columns in high-speed memory.",
        },
        {
          step: "02",
          title: "Vectorized Column Matching",
          detail: "The engine compares thousands of values at once using your computer processor's vector registers.",
        },
        {
          step: "03",
          title: "Pre-Join Aggregations & Filters",
          detail: "You can apply filters (e.g. status = 'active') or rollups (SUM, COUNT) before joining to keep data lean.",
        },
        {
          step: "04",
          title: "Instant Merged Output",
          detail: "The combined dataset is created in memory without writing temporary clutter to your hard drive.",
        },
      ],
      whyUseIt: [
        "Up to 20x faster than Pandas pd.merge() or database staging tables.",
        "Prevents out-of-memory crashes when joining tables with hundreds of thousands of rows.",
        "Generates clean, readable SQL under the hood that you can inspect and copy.",
      ],
      useCases: [
        {
          industry: "Retail Analytics",
          title: "Transaction & Catalog Merging",
          description: "Merge 1,000,000 transaction rows with a 50,000-item product catalog in under 1 second.",
          icon: ShoppingBag,
        },
        {
          industry: "Telecommunications",
          title: "Call Detail Records",
          description: "Join millions of call records with cell tower location tables without server lag.",
          icon: Cpu,
        },
      ],
      proTips: [
        "Make sure both join columns share the same data type (e.g., both are numbers or both are text) for maximum speed.",
      ],
    },

    // ── 6. MACHINE LEARNING & AUTOML ────────────────────────────────────────
    {
      id: "automl-tournament",
      category: "automl",
      categoryTitle: "Machine Learning Intelligence",
      badge: "TOURNAMENT ARENA",
      title: "AutoML Model Tournament",
      description: "Train and compare LightGBM, XGBoost, CatBoost, and Random Forest in parallel with live leaderboard scoring.",
      breadcrumb: "Machine Learning > Model Tournament",
      icon: Cpu,
      callout: {
        title: "Machine Learning for Everyone",
        text: "You don't need a PhD in statistics or years of coding experience. Pick the column you want to predict, click 'Run Tournament', and DataForge trains and ranks the best AI models automatically.",
      },
      whatItIs:
        "The AutoML Tournament Engine makes predictive machine learning as simple as selecting a column in your spreadsheet. Want to know which customers are likely to cancel their subscriptions, predict house prices, or detect fraudulent transactions? Simply select that target column and click 'Run Tournament'. DataForge automatically checks for data leakage, handles missing values, trains top machine learning algorithms (LightGBM, XGBoost, CatBoost, Random Forest) side-by-side, and crowns the top-performing champion on a live leaderboard.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Select Your Target Column",
          detail: "Choose the column you want to predict (e.g., churn, revenue, or lead_converted).",
        },
        {
          step: "02",
          title: "Automatic Problem Detection",
          detail: "DataForge detects whether you need Classification (predicting yes/no or categories) or Regression (predicting continuous numbers/prices) and splits data into 80% training and 20% testing sets.",
        },
        {
          step: "03",
          title: "Leakage Audit & Preprocessing",
          detail: "The engine audits features for leakage risk (columns that cheat by containing future info), encodes text categories, and scales numbers.",
        },
        {
          step: "04",
          title: "Parallel Training & Leaderboard",
          detail: "Models train in parallel under identical cross-validation conditions. Review the live leaderboard ranking models by accuracy, ROC-AUC, F1-Score, or RMSE.",
        },
      ],
      whyUseIt: [
        "Brings advanced machine learning to business analysts without writing hundreds of lines of Scikit-Learn code.",
        "Objective benchmarking: never guess which algorithm works best on your unique dataset.",
        "One-click deployment: deploy your champion model to the Enterprise Model Registry or export a Docker container.",
      ],
      useCases: [
        {
          industry: "Subscription Businesses",
          title: "Customer Churn Prediction",
          description: "Predict churn probability 30 days before renewal to trigger retention campaigns.",
          icon: Users,
        },
        {
          industry: "Financial Services",
          title: "Credit Risk Classification",
          description: "Predict default probability for loan applicants based on financial history.",
          icon: LineChart,
        },
      ],
      proTips: [
        "Always check the Leakage Audit recommendations. Dropping columns that contain future information ensures your model performs just as well on new real-world data.",
      ],
    },
    {
      id: "automl-evaluation",
      category: "automl",
      categoryTitle: "Machine Learning Intelligence",
      badge: "FEATURE IMPACT",
      title: "Evaluation & Feature Importance",
      description: "Inspect ROC-AUC curves, confusion matrices, and the true underlying drivers behind model predictions.",
      breadcrumb: "Machine Learning > Evaluation",
      icon: LineChart,
      callout: {
        title: "No Black Boxes",
        text: "DataForge explains exactly why your model makes each prediction. The Feature Importance chart reveals which columns have the biggest influence on your business outcomes.",
      },
      whatItIs:
        "Training an AI model is only half the battle—you also need to know if you can trust it and what it learned from your data. The Evaluation module gives you an easy-to-read report card. It breaks down model performance using clear accuracy metrics (ROC-AUC, Precision, Recall, Confusion Matrix) and ranks your columns by Feature Importance, showing stakeholders the exact business factors that drive results.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Review Accuracy Metrics",
          detail: "Check your model's score on unseen test data (Accuracy, ROC-AUC, Precision, Recall for classification, or RMSE and R² for regression).",
        },
        {
          step: "02",
          title: "Inspect the Confusion Matrix",
          detail: "See how many predictions were correct versus false positives (false alarms) or false negatives (missed cases).",
        },
        {
          step: "03",
          title: "Check Feature Importance Rankings",
          detail: "Examine the bar chart showing which columns have the strongest influence on the predictions (e.g., 'Discount percentage is the #1 driver of churn').",
        },
        {
          step: "04",
          title: "Actionable Business Takeaways",
          detail: "Use these drivers to change business strategy (like reducing extreme discounts or improving customer support response times).",
        },
      ],
      whyUseIt: [
        "Understand exactly what drives predictions instead of relying on mystery 'black-box' algorithms.",
        "Identify false alarms and missed predictions to tune your business thresholds.",
        "Provide transparent explanations to leadership, auditors, and regulators.",
      ],
      useCases: [
        {
          industry: "Human Resources",
          title: "Employee Retention Drivers",
          description: "Discover whether commute time, salary, or tenure has the biggest impact on turnover.",
          icon: Users,
        },
        {
          industry: "Insurance",
          title: "Claim Severity Analysis",
          description: "Find out which risk factors contribute most to high-cost claims.",
          icon: ShieldAlert,
        },
      ],
      proTips: [
        "If a single feature accounts for more than 75% of model importance, double check that it isn't an ID column or a target leakage column that accidentally reveals the answer.",
      ],
    },
    {
      id: "automl-docker",
      category: "automl",
      categoryTitle: "Machine Learning Intelligence",
      badge: "DEPLOY ANYWHERE",
      title: "Production Docker Deployment",
      description: "Download a production-ready Docker container with trained model weights and a FastAPI prediction server.",
      breadcrumb: "Machine Learning > Docker Deployment",
      icon: Boxes,
      callout: {
        title: "Instant Engineering Handoff",
        text: "The exported container includes pre-built REST API endpoints (/predict and /health) and interactive Swagger API documentation ready to run on any cloud platform.",
      },
      whatItIs:
        "Once you have trained a champion machine learning model, how do you actually put it to work in your company's website or mobile app? Traditionally, handing a model over to software engineers can take weeks of rewriting code. DataForge solves this by packaging your trained model, feature transformers, and a high-speed FastAPI web server into a standalone Docker container with one click.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Click 'Download Docker Container'",
          detail: "In the AutoML tab, click the export button to download a complete container zip archive.",
        },
        {
          step: "02",
          title: "Inspect Pre-Built FastAPI Code",
          detail: "The container includes an API server with /predict endpoints, request validation, and interactive Swagger docs at /docs.",
        },
        {
          step: "03",
          title: "Build and Run with One Command",
          detail: "Run 'docker build -t my-model .' and 'docker run -p 8000:8000 my-model' on any laptop, server, or cloud cluster.",
        },
        {
          step: "04",
          title: "Send Live Predictions",
          detail: "Send JSON data from your app to the /predict endpoint and receive instant prediction scores and probabilities in milliseconds.",
        },
      ],
      whyUseIt: [
        "Eliminates weeks of engineering friction when moving machine learning models from prototype to production.",
        "Docker guarantees that the model runs with the exact same dependencies and accuracy in production as it did in training.",
        "Ready to deploy to Google Cloud Run, AWS ECS, Kubernetes, or Azure App Service.",
      ],
      useCases: [
        {
          industry: "Software Engineering",
          title: "Real-Time Scoring Microservice",
          description: "Deploy the customer churn model as an internal microservice called by your CRM app.",
          icon: Terminal,
        },
        {
          industry: "Mobile Apps",
          title: "E-Commerce Recommendation API",
          description: "Serve real-time product recommendations to mobile app shoppers.",
          icon: ShoppingBag,
        },
      ],
      proTips: [
        "Open http://localhost:8000/docs in your browser after running the container to test predictions interactively using the built-in Swagger UI.",
      ],
    },

    // ── 7. AI MULTI-AGENT INTELLIGENCE ──────────────────────────────────────
    {
      id: "ai-chat",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "NATURAL LANGUAGE",
      title: "Natural Language Query Engine",
      description: "Ask questions in plain English and receive instant calculations, explanations, and interactive charts.",
      breadcrumb: "AI Intelligence > Natural Language Query Engine",
      icon: Bot,
      callout: {
        title: "Mathematical Grounding & Strict Privacy Boundaries",
        text: "The AI query engine never hallucinates figures. It generates sandboxed Python code that executes deterministically against your in-memory dataset, ensuring 100% mathematical accuracy with zero external data leaks.",
      },
      whatItIs:
        "The AI Natural Language Query Engine lets anyone explore datasets conversationally without knowing SQL, Python, or spreadsheet formulas. Simply type what you want to know—such as 'What were our top 5 selling products last quarter?' or 'Compare average deal size across sales territories.' The engine evaluates your question, dispatches the task to the right specialized domain agent, calculates the answer with verified arithmetic, and renders an interactive chart directly in the chat stream.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Privacy Consent & Workspace Handshake",
          detail: "Accept the one-time privacy consent banner. Your dataset schema is inspected locally to establish valid column names, data types, and row counts.",
        },
        {
          step: "02",
          title: "Conversational Query Submission",
          detail: "Type your query into the chat input, or select an intelligent suggestion chip generated dynamically from your active columns.",
        },
        {
          step: "03",
          title: "Supervisor Intent Arbitration",
          detail: "The Chief Supervisor Agent inspects the prompt. Ambiguous queries are evaluated via Google Gemini (gemini-2.5-flash) structured JSON routing, while direct tasks fast-path to dedicated agents.",
        },
        {
          step: "04",
          title: "Sandboxed Execution & Ground-Truth Verification",
          detail: "The AnalyticsAgent computes the result in an AST-isolated sandbox. The Supervisor verifies the computed values against the generated explanation before streaming the answer.",
        },
      ],
      whyUseIt: [
        "Enables non-technical business stakeholders to extract answers in seconds without waiting for engineering backlogs.",
        "Guarantees real arithmetic: calculations are performed by Python/NumPy, not guessed by generative language models.",
        "Zero data egress: raw row-level records are never shared with third-party servers.",
      ],
      useCases: [
        {
          industry: "Executive Leadership",
          title: "Real-Time Meeting Inquiries",
          description: "Instantly answer 'Which product category drove 80% of our Q3 revenue?' during executive strategy meetings.",
          icon: Building,
        },
        {
          industry: "Supply Chain",
          title: "Stock Alert Audits",
          description: "Ask 'Which warehouses have fewer than 25 units of SKU-402 left in stock?' to resolve fulfillment bottlenecks.",
          icon: ShoppingBag,
        },
      ],
      proTips: [
        "Ask conversational follow-up questions like 'Now break that down by region' or 'Exclude orders with zero discount'.",
        "Click the copy button on code snippets to inspect or reuse the exact Pandas logic generated by the engine.",
      ],
    },
    {
      id: "ai-orchestrator",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "COORDINATION",
      title: "SupervisorAgent: Multi-Agent Dispatcher",
      description: "How DataForge coordinates specialized domain agents—Cleaner, AutoML, Pipeline, Analytics, and Visualizer—under a Chief Supervisor.",
      breadcrumb: "AI Intelligence > Natural Language Query > SupervisorAgent",
      icon: Workflow,
      callout: {
        title: "Zero-Latency Intercepts & Ground-Truth Synchronization",
        text: "The SupervisorAgent intercepts conversational pleasantries with zero latency and synchronizes all LLM text against raw Python calculation output to eliminate hallucinations completely.",
      },
      whatItIs:
        "SupervisorAgent ('Chief Data Analyst') serves as the central brain of DataForge's multi-agent system. When a query arrives, the Supervisor first checks for standard conversational intercepts (greetings, identity, schema summaries) to deliver instant responses with zero external API calls. For operational requests, it routes tasks to specialized agents (CleanerAgent, AutoMLAgent, PipelineAgent, AnalyticsAgent, VisualizerAgent). Finally, it runs Ground Truth Synchronization, programmatically verifying that every number mentioned in the final response matches the exact math computed by the sandbox.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Zero-Latency Conversational Intercepts",
          detail: "Greetings ('hello', 'help') and metadata requests ('describe dataset', 'what columns exist') trigger pre-compiled pattern matchers, returning summaries in under 5ms with zero token cost.",
        },
        {
          step: "02",
          title: "Deterministic Fast-Path vs. Gemini Router",
          detail: "Unambiguous operations ('clean missing values', 'predict churn', 'export airflow dag') dispatch immediately. Ambiguous queries are routed via Gemini 2.5 Flash using structured AgentSelectionDecision JSON schemas.",
          codeSnippet: "class AgentSelectionDecision(BaseModel):\n    chosen_agent: Literal['CleanerAgent', 'AutoMLAgent', 'PipelineAgent', 'AnalyticsAgent', 'VisualizerAgent']\n    reason: str\n    target_col: Optional[str]",
          codeLang: "python",
        },
        {
          step: "03",
          title: "Fuzzy Entity & Column Resolution",
          detail: "Resolves minor typos, spacing discrepancies, and casing differences in user queries (e.g., 'cstmr rev' maps cleanly to 'customer_revenue').",
        },
        {
          step: "04",
          title: "Ground Truth Mathematical Synchronization",
          detail: "The synchronize_ground_truth() pipeline intercepts the LLM's suggested narrative, checks it against raw array results from AnalyticsAgent, and corrects any discrepancies before display.",
        },
      ],
      whyUseIt: [
        "Eliminates LLM hallucination: figures in text answers are guaranteed to match the dataset.",
        "Saves costs and time: conversational pleasantries are answered locally without token consumption.",
        "Coordinates complex multi-step workflows across data cleaning, machine learning, and visualization seamlessly.",
      ],
      useCases: [
        {
          industry: "Data Engineering",
          title: "Autonomous Agent Handoffs",
          description: "A single prompt like 'clean outliers and plot customer age distribution' coordinates CleanerAgent, AnalyticsAgent, and VisualizerAgent in sequence.",
          icon: Sparkles,
        },
        {
          industry: "Enterprise AI",
          title: "Audited Conversational Queries",
          description: "Guarantees corporate leadership that numbers cited in executive briefings have been mathematically verified against ground truth.",
          icon: ShieldCheck,
        },
      ],
      codeExample: {
        filename: "supervisor_plan.json",
        lang: "json",
        code: `{\n  "selected_agent": "AnalyticsAgent",\n  "confidence": 0.99,\n  "reasoning": "User requested bivariate correlation between customer_age and purchase_total",\n  "answer": "### Correlation Analysis\\n\\n• Pearson Correlation: 0.742 (Strong Positive)\\n• P-value: < 0.001\\n• Sample Size: 12,450 rows",\n  "intent": "scatter_chart",\n  "code": "df[['customer_age', 'purchase_total']].dropna().corr()"\n}`,
      },
      proTips: [
        "Your GEMINI_API_KEY in .env automatically hot-reloads on your next message without restarting the server.",
        "If Google AI Studio returns HTTP 402 (prepayment credits depleted), DataForge activates its high-availability local engine while keeping answers clean with an isolated system banner.",
      ],
    },
    {
      id: "ai-agent-cleaner",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "DATA SANITIZATION",
      title: "CleanerAgent: Automated Hygiene & Rollbacks",
      description: "Automated missing value audits, median/mode imputation, IQR outlier clipping, and 1-click snapshot restoration.",
      breadcrumb: "AI Intelligence > Natural Language Query > CleanerAgent",
      icon: Sparkles,
      callout: {
        title: "Transactional Snapshot Rollbacks",
        text: "CleanerAgent creates an in-memory snapshot before applying any data transformations. Simply type 'undo' or 'revert' into the chat to restore your previous dataset state instantly.",
      },
      whatItIs:
        "CleanerAgent is DataForge's dedicated data sanitization specialist. Rather than requiring you to manually click through spreadsheet menus to find empty cells or strip formatting errors, CleanerAgent handles it directly from chat. You can say 'clean missing values', 'fill missing age with median', 'remove duplicate emails', or 'clip extreme outliers'. CleanerAgent computes quality score improvements, applies the transformations to the active workspace DataFrame, and records an undo snapshot so you are never locked into a change.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Conversational Cleaning Trigger",
          detail: "Type an operational request like 'clean missing values', 'impute with median', or 'clip outliers' into the chat box.",
        },
        {
          step: "02",
          title: "Missing Value Audit & Strategy Selection",
          detail: "CleanerAgent audits column null distributions. Numeric columns are imputed with the median (to avoid outlier skew), while categorical columns are imputed with the mode.",
          codeSnippet: "# CleanerAgent automated imputation\nnumeric_impute = df[col].median()\ncategorical_impute = df[col].mode().iloc[0] if not df[col].mode().empty else 'Unknown'",
          codeLang: "python",
        },
        {
          step: "03",
          title: "IQR-Based Outlier Boundary Capping",
          detail: "Identifies extreme numeric values using 1.5x Interquartile Range (IQR) capping, keeping extreme records within realistic operational boundaries without deleting rows.",
        },
        {
          step: "04",
          title: "Live Quality Score & Workspace Sync",
          detail: "Updates the active dataset in memory and calculates data completeness improvement (e.g. 'Completeness improved from 82.4% to 100.0%').",
        },
      ],
      whyUseIt: [
        "Sanitizes dirty datasets in seconds without writing manual Pandas scripts.",
        "Preserves sample sizes: outlier capping and median imputation keep valid records from being needlessly dropped.",
        "Reversible by design: typing 'undo' immediately reverts to the pre-cleaning snapshot.",
      ],
      useCases: [
        {
          industry: "Healthcare Analytics",
          title: "Patient Vitals Imputation",
          description: "Say 'clean dataset' to fill missing blood pressure readings with median values and flag anomalies.",
          icon: HeartPulse,
        },
        {
          industry: "Financial Services",
          title: "Income Outlier Clipping",
          description: "Say 'clip outliers on applicant_income' to cap extreme multimillion-dollar entries before credit scoring.",
          icon: LineChart,
        },
      ],
      codeExample: {
        filename: "cleaner_agent_summary.json",
        lang: "json",
        code: `{\n  "agent": "CleanerAgent",\n  "tool": "clean_dataset_tool",\n  "status": "completed",\n  "message": "Dataset cleaned successfully.",\n  "stats": {\n    "original_rows": 10000,\n    "cleaned_rows": 9984,\n    "initial_quality": 81.5,\n    "final_quality": 100.0,\n    "actions_applied": [\n      "Filled missing customer_age with median (34)",\n      "Imputed state with mode ('CA')",\n      "Capped annual_income outliers above $240,000"\n    ]\n  }\n}`,
      },
      proTips: [
        "Type 'audit missing values' in chat to see a column-by-column breakdown of empty cells before choosing a cleaning strategy.",
        "If you want to reverse a cleaning operation, simply type 'undo' in the chat sidebar to restore the previous state.",
      ],
    },
    {
      id: "ai-agent-automl",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "MACHINE LEARNING",
      title: "AutoMLAgent: Predictive Modeling Advisor",
      description: "Automated target detection, task formulation, mutual information signal ranking, and algorithm tournament recommendations.",
      breadcrumb: "AI Intelligence > Natural Language Query > AutoMLAgent",
      icon: Cpu,
      callout: {
        title: "Rigorous Mathematical Task Detection",
        text: "AutoMLAgent audits target column cardinalities and distributions to automatically determine whether your problem is Binary Classification, Multiclass Classification, or Regression.",
      },
      whatItIs:
        "AutoMLAgent is DataForge's machine learning strategist. When you ask 'Can we predict customer churn?' or 'How do I forecast next month's sales?', AutoMLAgent inspects the target variable, detects the task architecture, identifies high-signal predictors using mutual information and correlation, audits class imbalance ratios, and recommends top-performing algorithms (LightGBM, XGBoost, Random Forest, Ridge Regression). It then prepares the parameters for 1-click execution in DataForge's AutoML Tournament Studio.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Target Detection & Intent Extraction",
          detail: "Type 'predict [column_name]' or 'forecast sales'. AutoMLAgent isolates the candidate target variable and checks its data type.",
        },
        {
          step: "02",
          title: "Task Classification (Binary, Multiclass, Regression)",
          detail: "Determines whether the target is discrete labels (Classification) or continuous values (Regression). Low cardinality (e.g. 0/1 or Yes/No) triggers binary classification with ROC-AUC scoring.",
        },
        {
          step: "03",
          title: "High-Signal Feature Selection",
          detail: "Computes mutual information scores between each candidate column and the target, highlighting the strongest predictive features while warning against data leakage.",
        },
        {
          step: "04",
          title: "Algorithm Benchmark Formulation",
          detail: "Recommends benchmark algorithms suited to your data size and target distribution (e.g. LightGBM for large tabular datasets, Random Forest for robust baselines).",
        },
      ],
      whyUseIt: [
        "Takes the guesswork out of model selection: tells you exactly which algorithms are suited for your dataset.",
        "Identifies predictive drivers before training starts, saving compute time and effort.",
        "Detects severe class imbalance early and recommends appropriate evaluation metrics (PR-AUC, F1-Score).",
      ],
      useCases: [
        {
          industry: "Telecommunications & SaaS",
          title: "Customer Churn Formulation",
          description: "Say 'predict churn' to detect binary classification, evaluate tenure correlations, and recommend LightGBM.",
          icon: Users,
        },
        {
          industry: "Real Estate & Commerce",
          title: "Property Price Valuation",
          description: "Say 'predict listing_price' to detect continuous regression and benchmark XGBoost with RMSE optimization.",
          icon: Building,
        },
      ],
      codeExample: {
        filename: "automl_formulation.json",
        lang: "json",
        code: `{\n  "agent": "AutoMLAgent",\n  "task": "classification",\n  "target_column": "churned",\n  "recommended_models": ["LightGBM", "XGBoost", "Random Forest", "Logistic Regression"],\n  "top_features": ["monthly_charges", "total_tenure_months", "contract_type", "support_tickets"],\n  "class_balance": {\n    "retained (0)": "73.4%",\n    "churned (1)": "26.6%",\n    "imbalance_ratio": "2.76:1"\n  }\n}`,
      },
      proTips: [
        "Ask AutoMLAgent 'What features correlate most with [target]?' to inspect feature importance before running tournaments.",
        "After AutoMLAgent formulates the problem, switch to the AutoML tab in your workspace to launch the full tournament with 1 click.",
      ],
    },
    {
      id: "ai-agent-pipeline",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "ETL COMPILER",
      title: "PipelineAgent: Enterprise ETL Compiler",
      description: "Generates production Apache Airflow DAGs, dbt SQL transformation models, and standalone Python CLI scripts from conversation.",
      breadcrumb: "AI Intelligence > Natural Language Query > PipelineAgent",
      icon: Code2,
      callout: {
        title: "Production-Grade Code Generation",
        text: "PipelineAgent compiles production-ready code with error handling, logging, retry policies, and schema contracts—ready to paste directly into git repositories.",
      },
      whatItIs:
        "PipelineAgent bridges the gap between ad-hoc data exploration and enterprise production data engineering. Once you have cleaned, merged, or analyzed your data in DataForge, you need to operationalize the workflow. Instead of re-writing the transformations from scratch in Python or SQL, simply say 'export airflow dag', 'generate dbt pipeline', or 'export python script' in chat. PipelineAgent compiles enterprise-ready code complete with imports, retry semantics, and schedule parameters.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Request Pipeline Format",
          detail: "Type 'export airflow dag', 'export dbt model', or 'generate python script' into the chat sidebar.",
        },
        {
          step: "02",
          title: "Workflow Inspection & Step Mapping",
          detail: "PipelineAgent inspects the cleaning history, column types, and data transformations applied to your active dataset.",
        },
        {
          step: "03",
          title: "Template Synthesis & Compilation",
          detail: "Generates syntactically verified code tailored to your target orchestration framework (e.g., @dag decorator in Airflow, {{ config() }} in dbt).",
        },
        {
          step: "04",
          title: "Direct Code Copy & Deployment Guidance",
          detail: "Renders the complete script in a syntax-highlighted code block with step-by-step instructions for placing it into production.",
        },
      ],
      whyUseIt: [
        "Saves data engineers hours of boilerplate code writing when moving analyses into production.",
        "Guarantees that production pipelines replicate the exact cleaning logic verified inside the workspace.",
        "Includes enterprise best practices: retry policies, execution timeouts, and structured logging.",
      ],
      useCases: [
        {
          industry: "Data Engineering",
          title: "Daily Airflow Ingestion DAGs",
          description: "Say 'export airflow dag' to generate a scheduled daily batch pipeline with alerting and retries.",
          icon: Workflow,
        },
        {
          industry: "Modern Data Stack",
          title: "dbt Dimensional Models",
          description: "Say 'export dbt' to compile staging SQL models with schema tests for Snowflake or BigQuery.",
          icon: Database,
        },
      ],
      codeExample: {
        filename: "dags/dataforge_etl_pipeline.py",
        lang: "python",
        code: `from airflow.decorators import dag, task\nfrom datetime import datetime, timedelta\nimport pandas as pd\n\n@dag(\n    schedule="@daily",\n    start_date=datetime(2026, 1, 1),\n    catchup=False,\n    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)}\n)\ndef dataforge_pipeline():\n    @task\n    def ingest_and_clean():\n        df = pd.read_parquet("s3://company-datalake/raw/data.parquet")\n        df["customer_age"] = df["customer_age"].fillna(df["customer_age"].median())\n        return df\n\n    ingest_and_clean()\n\ndataforge_pipeline()`,
      },
      proTips: [
        "Specify your preferred schedule in the prompt, e.g. 'export airflow dag scheduled to run every Monday at 6 AM'.",
        "PipelineAgent generates dbt schema.yml files with unique and not_null constraints automatically.",
      ],
    },
    {
      id: "ai-agent-analytics",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "SANDBOXED MATH",
      title: "AnalyticsAgent: Sandboxed Statistical Engine",
      description: "AST-isolated Python execution, NumPy/Pandas vectorization, Pearson correlation matrices, and deterministic offline fallbacks.",
      breadcrumb: "AI Intelligence > Natural Language Query > AnalyticsAgent",
      icon: Terminal,
      callout: {
        title: "AST-Isolated Python Execution Sandbox",
        text: "AnalyticsAgent inspects generated Python code with an Abstract Syntax Tree (AST) validator before execution, blocking dangerous imports (os, sys, socket) and disk tampering.",
      },
      whatItIs:
        "AnalyticsAgent is the quantitative math engine of DataForge. When you ask for correlations, quantiles, variance, groupings, or aggregations, AnalyticsAgent formulates vectorized Pandas and NumPy operations, executes them inside an isolated Python sandbox, and returns the computed results. If external AI APIs (like Google Gemini) are unavailable or credits are exhausted (HTTP 402), AnalyticsAgent automatically engages its high-availability local deterministic engine to calculate exact answers without missing a beat.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Quantitative Code Synthesis",
          detail: "Translates the user's analytical question into vectorized Pandas or NumPy code expressions.",
        },
        {
          step: "02",
          title: "Abstract Syntax Tree (AST) Security Scan",
          detail: "Pre-scans the Python code. Dangerous calls (exec, eval, __import__, open, socket) are rejected before execution.",
        },
        {
          step: "03",
          title: "In-Memory Vectorized Execution",
          detail: "Executes computations against the in-memory DataFrame slice, assigning the final result to raw_result.",
        },
        {
          step: "04",
          title: "Deterministic Fallback Engagement",
          detail: "If Gemini API credits are depleted or network is offline, the local rule-based engine computes Pearson correlations, grouped sums, and distributions locally.",
        },
      ],
      whyUseIt: [
        "Calculates real math: eliminates LLM arithmetic hallucinations with true Python runtime execution.",
        "High security: the AST sandbox guarantees that no untrusted code can compromise your machine or environment.",
        "High availability: continues delivering statistical insights even when third-party cloud AI APIs are down.",
      ],
      useCases: [
        {
          industry: "Scientific Research",
          title: "Correlation Matrix Audits",
          description: "Ask 'Show correlation between age, income, and purchase amount' to calculate Pearson coefficients and p-values.",
          icon: LineChart,
        },
        {
          industry: "E-Commerce Analytics",
          title: "Customer Segment Aggregations",
          description: "Ask 'What is the median order value by loyalty tier?' to run grouped quantile aggregations.",
          icon: ShoppingBag,
        },
      ],
      codeExample: {
        filename: "analytics_execution.py",
        lang: "python",
        code: `# Safe sandboxed calculation executed by AnalyticsAgent\ndef analyze(df: pd.DataFrame):\n    # Grouped quantile aggregation\n    result = (\n        df.groupby("customer_tier")["order_value"]\n        .agg(median="median", mean="mean", count="count")\n        .reset_index()\n    )\n    return result`,
      },
      proTips: [
        "You can ask for advanced statistical metrics like 'What is the 95th percentile of response time?' or 'Show standard deviation of pricing'.",
        "AnalyticsAgent automatically handles missing values during correlations by dropping incomplete pairs.",
      ],
    },
    {
      id: "ai-agent-visualizer",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "CHART SYNTHESIS",
      title: "VisualizerAgent: Chart.js Visual Synthesis",
      description: "Compiles mathematical metrics into responsive Chart.js interactive Bar, Line, Scatter, Pie, and Histogram visualizations.",
      breadcrumb: "AI Intelligence > Natural Language Query > VisualizerAgent",
      icon: BarChart3,
      callout: {
        title: "Aesthetic Rules & Anti-Misleading Safeguards",
        text: "VisualizerAgent enforces strict data visualization rules—such as strictly prohibiting line charts for unordered categorical dimensions—to ensure your reports are always statistically valid.",
      },
      whatItIs:
        "VisualizerAgent is DataForge's visual communication expert. Numbers and tables alone are hard to parse during quick reviews; VisualizerAgent transforms computed metrics into beautiful, interactive Chart.js charts rendered right inside your chat stream. It automatically selects the optimal visualization type (Bar, Line, Scatter, Pie/Doughnut, Histogram), aligns colors with the active theme palette, formats tooltips with appropriate currency and percentage symbols, and lets you copy or export the chart configuration.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Visual Intent Formulation",
          detail: "Evaluates the analytical outcome (e.g. trend over time, part-to-whole ratio, categorical comparison, bivariate relationship).",
        },
        {
          step: "02",
          title: "Chart Type Selection & Rule Validation",
          detail: "Picks the optimal chart intent. Unordered categories are routed to Bar or Pie charts; continuous time-series are routed to Line charts; numeric distributions are routed to Histograms.",
        },
        {
          step: "03",
          title: "Design System Token Harmony",
          detail: "Applies DataForge's vibrant CSS variables and curated palette tokens to ensure perfect contrast in both Dark and Light modes.",
        },
        {
          step: "04",
          title: "Interactive Synthesis & Tooltip Formatting",
          detail: "Compiles full Chart.js specifications with responsive aspect ratios, hover tooltips, and interactive legend toggles.",
        },
      ],
      whyUseIt: [
        "Instantly visualizes answers: no need to manually construct charts in separate design tools.",
        "Prevents misleading visualizations: automatically enforces proper statistical plotting standards.",
        "Theme-responsive: charts look sharp and legible whether you are in Dark or Light mode.",
      ],
      useCases: [
        {
          industry: "Sales Leadership",
          title: "Territory Revenue Comparisons",
          description: "Generates an interactive horizontal Bar chart comparing sales revenue across 10 regions.",
          icon: BarChart3,
        },
        {
          industry: "Financial Planning",
          title: "Monthly Cash Flow Trends",
          description: "Renders a smooth Line chart showing 12-month net profit progression with hover markers.",
          icon: LineChart,
        },
      ],
      codeExample: {
        filename: "chart_spec.json",
        lang: "json",
        code: `{\n  "type": "bar",\n  "data": {\n    "labels": ["Electronics", "Apparel", "Home Goods", "Automotive"],\n    "datasets": [{\n      "label": "Total Revenue ($)",\n      "data": [452000, 284000, 195000, 122000],\n      "backgroundColor": "rgba(99, 102, 241, 0.85)",\n      "borderColor": "rgba(99, 102, 241, 1)",\n      "borderWidth": 1.5\n    }]\n  },\n  "options": {\n    "responsive": true,\n    "plugins": { "tooltip": { "enabled": true } }\n  }\n}`,
      },
      proTips: [
        "Click any dataset label in the chart legend to toggle that series on or off interactively.",
        "You can request specific chart formats by asking 'make a pie chart of department spend' or 'plot distribution as a histogram'.",
      ],
    },
    {
      id: "ai-sessions",
      category: "ai-analyst",
      categoryTitle: "AI Multi-Agent Intelligence",
      badge: "THREADS",
      title: "Session Management & History",
      description: "Organize different analytical inquiries into named chat threads with easy renaming and deletion.",
      breadcrumb: "AI Intelligence > Natural Language Query > Session History",
      icon: Terminal,
      callout: {
        title: "Never Lose Your Findings",
        text: "DataForge saves your chat sessions alongside your dataset so you can return to previous questions, charts, and answers whenever you reopen your project.",
      },
      whatItIs:
        "When exploring data, you often investigate multiple different questions—like auditing revenue trends, checking shipping delays, or exploring customer churn. To keep your workspace tidy, DataForge lets you create dedicated chat threads for each topic. You can give them custom names, switch between them with one click, and keep your thought process clearly organized.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Click 'New Chat'",
          detail: "Click the 'New Chat' button in the chat sidebar to start a clean thread for a new question or project.",
        },
        {
          step: "02",
          title: "Rename with Descriptive Titles",
          detail: "Click the pencil icon next to any session name to rename it (e.g. 'Q3 Regional Sales' or 'Return Rate Investigation').",
        },
        {
          step: "03",
          title: "Switch Between Sessions",
          detail: "Click any session in your history list to instantly reload earlier questions, answers, and interactive charts.",
        },
        {
          step: "04",
          title: "Clean Up Old Threads",
          detail: "Click the trash icon next to a session to delete it with a quick confirmation when you are done.",
        },
      ],
      whyUseIt: [
        "Keeps different analytical investigations separated so questions don't get mixed up.",
        "Allows you to return to earlier calculations and charts whenever you need them.",
        "Makes it easy to walk teammates through your analytical journey step-by-step.",
      ],
      useCases: [
        {
          industry: "Project Management",
          title: "Topic-Based Investigations",
          description: "Keep separate chat threads for Marketing ROI, Product Churn, and Inventory Health.",
          icon: LineChart,
        },
        {
          industry: "Teammate Collaboration",
          title: "Reviewing Past Queries",
          description: "Allow team members to review previous data questions and verify the logic.",
          icon: Users,
        },
      ],
      proTips: [
        "Give your chat sessions descriptive names right away so you can quickly find your favorite charts and answers later.",
      ],
    },

    // ── 8. PRODUCTION EXPORTS & DELIVERY ────────────────────────────────────
    {
      id: "exports-datasets",
      category: "exports",
      categoryTitle: "Production Exports",
      badge: "OPEN FORMATS",
      title: "Multi-Format Dataset Downloads",
      description: "Download clean datasets in CSV, Excel (.xlsx), Apache Parquet, or JSON with zero vendor lock-in.",
      breadcrumb: "Exports > Dataset Downloads",
      icon: Download,
      callout: {
        title: "You Always Own Your Data",
        text: "DataForge never traps your data. Download your transformed tables in standard formats ready for Excel, data warehouses, or API services.",
      },
      whatItIs:
        "Once you have cleaned up messy rows, imputed missing cells, and merged multiple spreadsheets together, you need to share or use that clean data. DataForge gives you complete freedom with multi-format downloads. Whether you need an Excel file for your business team, a CSV for a simple spreadsheet, an Apache Parquet file for cloud databases, or JSON for software developers, you can download it with one click.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Click 'Export' in the Workspace",
          detail: "Open the export menu from the workspace navigation bar.",
        },
        {
          step: "02",
          title: "Select Your Preferred Format",
          detail: "Choose between CSV (standard spreadsheets), Excel (.xlsx with formatted sheets), Apache Parquet (compressed cloud data), or JSON.",
        },
        {
          step: "03",
          title: "High-Speed Streaming Download",
          detail: "DataForge streams the file directly to your browser download folder in seconds.",
        },
        {
          step: "04",
          title: "Open in Any Tool",
          detail: "Open the clean file in Microsoft Excel, Google Sheets, Python, Tableau, Power BI, or load it into Snowflake.",
        },
      ],
      whyUseIt: [
        "Zero vendor lock-in: your data remains 100% portable and compatible with every major tool.",
        "Parquet format cuts file sizes by up to 80% while speeding up cloud warehouse queries by 10x.",
        "Preserves clean column data types so numbers and dates don't get corrupted in spreadsheets.",
      ],
      useCases: [
        {
          industry: "Business Reporting",
          title: "Monthly Excel Handoff",
          description: "Export cleaned sales tables as .xlsx files ready for financial modeling.",
          icon: FileSpreadsheet,
        },
        {
          industry: "Cloud Warehouses",
          title: "Snowflake & BigQuery Ingestion",
          description: "Export clean Parquet files to load directly into cloud data warehouses.",
          icon: Database,
        },
      ],
      proTips: [
        "If you are loading data into Snowflake, BigQuery, or Databricks, choose Parquet format for maximum speed and lower storage costs.",
      ],
    },
    {
      id: "exports-pipeline",
      category: "exports",
      categoryTitle: "Production Exports",
      badge: "CODE EXPORT",
      title: "Pipeline Code & dbt Models",
      description: "Export visual transformations as standalone Python scripts, dbt SQL models, or Airflow DAGs.",
      breadcrumb: "Exports > Pipeline Code",
      icon: Code2,
      callout: {
        title: "Bridge Visual Clicks to Production Code",
        text: "Never rewrite visual transformations by hand. DataForge automatically writes clean Python, dbt SQL, or Airflow code matching every visual rule you applied.",
      },
      whatItIs:
        "One of the biggest headaches in data work is doing something visually in a spreadsheet, and then having to explain to software engineers how to write code to repeat it every day. The Pipeline Studio solves this automatically. Every visual cleaning step, outlier rule, and join you execute is translated into clean, readable code in your choice of Python (Pandas), dbt SQL models, or Apache Airflow DAGs.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Open the Pipeline Studio Modal",
          detail: "Click 'Pipeline Studio' in your workspace header.",
        },
        {
          step: "02",
          title: "Choose Your Target Framework",
          detail: "Switch between tabs: Python (standalone Pandas/NumPy script), dbt (SQL transformation model), Airflow (orchestrated DAG), or Stored Procedure recipe.",
        },
        {
          step: "03",
          title: "Review Generated Code",
          detail: "Inspect the readable code with clear comments explaining each transformation, threshold, and column modified.",
        },
        {
          step: "04",
          title: "Copy or Download",
          detail: "Click 'Copy Code' or 'Download' to commit the script directly to your company's Git repository or CI/CD pipeline.",
        },
      ],
      whyUseIt: [
        "Bridges the gap between business analysts and software/data engineers effortlessly.",
        "Eliminates human translation errors when turning business requirements into production code.",
        "Zero proprietary code: runs on standard open-source tools with no external DataForge dependency.",
      ],
      useCases: [
        {
          industry: "Analytics Engineering",
          title: "dbt Staging Models",
          description: "Generate dbt SQL staging models from visual cleaning recipes for your data warehouse.",
          icon: Terminal,
        },
        {
          industry: "Data Engineering",
          title: "Airflow DAG Creation",
          description: "Download an Apache Airflow pipeline script for automated nightly data transformation.",
          icon: Layers,
        },
      ],
      proTips: [
        "The generated Python script includes docstrings detailing which columns were modified, making code reviews easy for teammates.",
      ],
    },
    {
      id: "exports-deck-pdf",
      category: "exports",
      categoryTitle: "Production Exports",
      badge: "PRINTABLE PDF",
      title: "Executive Decks & PDF Export",
      description: "Export boardroom-ready presentation decks and executive PDF summaries with one click.",
      breadcrumb: "Exports > Executive Decks",
      icon: Presentation,
      callout: {
        title: "Crisp Vector Visuals",
        text: "All charts and scorecards in exported reports use high-resolution vector graphics, ensuring they look razor-sharp on retina displays and printed pages.",
      },
      whatItIs:
        "Executive Decks and PDF Export allow you to turn raw spreadsheets into professional, polished presentations ready for executive leadership, investors, or board meetings. You don't have to spend hours taking screenshots and pasting them into slide templates. DataForge generates complete executive summaries and 5-slide presentation decks formatted specifically for landscape printing and PDF export.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Open Presentation or Business Report View",
          detail: "In the EDA tab, open either the 5-Slide Presentation Deck or the AI Business Report.",
        },
        {
          step: "02",
          title: "Review Slides and Metrics",
          detail: "Verify the KPI cards, distribution drivers, correlation heatmaps, and executive takeaways.",
        },
        {
          step: "03",
          title: "Click 'Print Deck' or 'Download PDF'",
          detail: "DataForge launches your browser's print dialog with dedicated print stylesheets active.",
        },
        {
          step: "04",
          title: "Save as Clean Landscape PDF",
          detail: "Select 'Save as PDF' and 'Landscape' orientation. Each slide prints cleanly on its own sheet with zero overflow.",
        },
      ],
      whyUseIt: [
        "Saves hours of tedious manual formatting in PowerPoint or Google Slides.",
        "Vector SVG charts stay crystal clear at any zoom level or printed size.",
        "Instant deliverables: have executive-ready handouts prepared in minutes.",
      ],
      useCases: [
        {
          industry: "Management Consulting",
          title: "Client Wrap-Up Packets",
          description: "Deliver a 5-page landscape PDF deck summarizing findings at the conclusion of an engagement.",
          icon: Building,
        },
        {
          industry: "Corporate Leadership",
          title: "Quarterly Strategic Reviews",
          description: "Print clean slide packets for physical distribution during board reviews.",
          icon: LineChart,
        },
      ],
      proTips: [
        "Turn on 'Background graphics' in your browser's print options to ensure card backgrounds and accent colors print richly.",
      ],
    },

    // ── 9. TEAM & SECURITY GOVERNANCE ───────────────────────────────────────
    {
      id: "governance-roles",
      category: "governance",
      categoryTitle: "Deployment & Governance",
      badge: "3 SIMPLE ROLES",
      title: "3-Tier Roles & Access Permissions",
      description: "Clear team access management with exactly 3 role levels: Viewer, Analyst, and Admin.",
      breadcrumb: "Governance > 3-Tier Roles",
      icon: Users,
      callout: {
        title: "Simple & Foolproof",
        text: "No confusing matrices of 50 different toggles. DataForge uses 3 intuitive roles so everyone on your team knows exactly who can view, analyze, and manage.",
      },
      whatItIs:
        "Managing team permissions shouldn't require a computer science degree or hours of navigating confusing menus. To prevent permission sprawl and accidental data modifications, DataForge organizes access into exactly 3 clear, intuitive roles: Viewer, Analyst, and Admin. This makes it effortless to share insights with department managers while ensuring that only authorized colleagues can modify data or invite new members.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Viewer (Level 1 - Read Only)",
          detail: "Can inspect tables, explore charts, read EDA reports, and ask questions in the AI chat without being able to modify data or change cleaning rules.",
        },
        {
          step: "02",
          title: "Analyst (Level 2 - Full Analysis)",
          detail: "Can upload new files, run 1-click cleaning, create custom rules, join tables, train AutoML models, and export clean datasets.",
        },
        {
          step: "03",
          title: "Admin (Level 3 - Full Management)",
          detail: "Can manage organization members, change roles, configure database connection credentials in the Vault, and review audit logs.",
        },
        {
          step: "04",
          title: "Instant Role Switching",
          detail: "Dataset owners and Admins can adjust any member's role anytime from the Share modal or Team Governance drawer.",
        },
      ],
      whyUseIt: [
        "Eliminates permission confusion: everyone knows exactly what each role is allowed to do.",
        "Protects clean data: Viewers can explore dashboards freely without any risk of accidentally deleting or modifying records.",
        "Audit-ready governance: ensures your organization meets internal security and data compliance policies.",
      ],
      useCases: [
        {
          industry: "Department Sharing",
          title: "Executive Stakeholder Access",
          description: "Give department heads Viewer access so they can view live charts without altering clean data.",
          icon: Building,
        },
        {
          industry: "Analytics Teams",
          title: "Team Model Building",
          description: "Assign data analysts the Analyst role so they can collaborate on cleaning and AutoML.",
          icon: Users,
        },
      ],
      proTips: [
        "When sharing with outside clients or executives, always assign the Viewer role for safe, worry-free exploration.",
      ],
    },
    {
      id: "governance-sharing",
      category: "governance",
      categoryTitle: "Deployment & Governance",
      badge: "COLLABORATION",
      title: "Dataset Sharing & Link Access",
      description: "Share datasets with Restricted invites or secret link access, complete with teammate avatars and instant link revocation.",
      breadcrumb: "Governance > Dataset Sharing",
      icon: Share2,
      callout: {
        title: "Google Docs Simplicity with Enterprise Protection",
        text: "Click 'Share' on any dataset to invite teammates by email or generate a shareable link. Choose between Restricted access or Anyone with the link.",
      },
      whatItIs:
        "Collaborating on data in DataForge is as simple and natural as sharing a Google Doc. Every dataset features an intuitive Share dialog where you can invite colleagues, see their real names and profile pictures, set their role (Viewer, Analyst, or Admin), and copy a secure link. If a link is ever shared by accident, you can revoke it instantly with one click.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Click 'Share' in the Workspace",
          detail: "Click the 'Share' button in the top navigation bar to open the sharing settings and see who has access.",
        },
        {
          step: "02",
          title: "Invite Teammates by Email",
          detail: "Type a colleague's email address, select their role (Viewer, Analyst, or Admin), and click 'Invite'.",
        },
        {
          step: "03",
          title: "Choose Link Access Mode",
          detail: "Pick 'Restricted' (only invited team members can open the link) or 'Anyone with the link' (anyone with the secret URL can open the dataset).",
        },
        {
          step: "04",
          title: "Copy Link & Instant Revoke",
          detail: "Click 'Copy link' to paste into Slack or email. If you ever need to cancel access, click 'Reset link' to revoke the old URL and generate a fresh one immediately.",
        },
      ],
      whyUseIt: [
        "Clear visibility: see real collaborator names and profile pictures in your team access list.",
        "Prevents data tampering: Restricted mode ensures only authorized emails can view your project.",
        "Instant revocation: reset the link with one click if it is ever shared in the wrong channel.",
      ],
      useCases: [
        {
          industry: "Cross-Functional Teams",
          title: "Stakeholder Dashboards",
          description: "Share a Viewer link with company leadership so they can explore charts without login friction.",
          icon: Presentation,
        },
        {
          industry: "Collaborative Data Prep",
          title: "Peer Review",
          description: "Invite fellow analysts to inspect your cleaning rules and AutoML leaderboard.",
          icon: Users,
        },
      ],
      proTips: [
        "Look for the 'Shared by' badge at the top of the workspace to see the avatar and name of whoever created the original dataset.",
      ],
    },
    {
      id: "governance-security",
      category: "governance",
      categoryTitle: "Deployment & Governance",
      badge: "OWASP DEFENSE",
      title: "Enterprise OWASP Security & Framing",
      description: "Rigorous security headers, clickjacking defense, Content Security Policies, and safe report framing.",
      breadcrumb: "Governance > OWASP Security",
      icon: ShieldCheck,
      callout: {
        title: "Bank-Grade Protection",
        text: "API routes strictly enforce X-Frame-Options: DENY against clickjacking, while report endpoints dynamically enable secure SAMEORIGIN framing so interactive reports embed smoothly inside your workspace.",
      },
      whatItIs:
        "Enterprise data security isn't an afterthought in DataForge—it is built into every request. DataForge implements the Open Web Application Security Project (OWASP) security recommendations across all backend endpoints. This protects your company's data against malicious attacks like clickjacking, cross-site scripting (XSS), and MIME-sniffing, while ensuring that internal interactive reports load smoothly inside your workspace without broken iframe connections.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Clickjacking Defense",
          detail: "Default API endpoints enforce X-Frame-Options: DENY to stop malicious third-party websites from embedding your workspace.",
        },
        {
          step: "02",
          title: "Authorized Report Framing",
          detail: "Report routes (/eda/report and /reports/latest) dynamically provide X-Frame-Options: SAMEORIGIN and Content-Security-Policy frame-ancestors 'self' so your reports load smoothly inside your own workspace tabs.",
        },
        {
          step: "03",
          title: "Cross-Site Scripting & MIME Protection",
          detail: "Every HTTP response includes X-Content-Type-Options: nosniff and X-XSS-Protection: 1; mode=block to prevent browser tampering.",
        },
        {
          step: "04",
          title: "Token Authentication",
          detail: "API calls require secure bearer tokens, preventing unauthorized access across corporate networks.",
        },
      ],
      whyUseIt: [
        "Protects confidential company data from modern web vulnerabilities and clickjacking attacks.",
        "Passes corporate IT security audits and penetration tests (SOC 2, ISO 27001).",
        "Ensures seamless, reliable report embedding inside your browser without annoying iframe connection drops.",
      ],
      useCases: [
        {
          industry: "Banking & FinTech",
          title: "Security Compliance Audits",
          description: "Meet automated OWASP security header testing suites with 100% passing grades.",
          icon: ShieldAlert,
        },
        {
          industry: "Healthcare & Life Sciences",
          title: "Data Privacy Protection",
          description: "Prevent unauthorized third-party domains from framing sensitive medical metrics.",
          icon: HeartPulse,
        },
      ],
      proTips: [
        "Run pytest tests/test_security_headers.py in the backend test suite to verify that all HTTP security headers are operating correctly.",
      ],
    },
    {
      id: "governance-vault",
      category: "governance",
      categoryTitle: "Deployment & Governance",
      badge: "AUDIT TRAILS",
      title: "Shared Database Vault & Audit Trails",
      description: "Centralized encrypted database connections and an immutable chronological activity log.",
      breadcrumb: "Governance > Database Vault & Audits",
      icon: Lock,
      callout: {
        title: "Complete Transparency & Accountability",
        text: "Every dataset upload, cleaning operation, model training run, and file export is automatically recorded with timestamps and user details in an immutable audit log.",
      },
      whatItIs:
        "The Shared Database Vault and Audit Trails provide the administrative backbone for organization-wide data governance. It combines two vital security features: a secure, encrypted vault where admins can store database credentials (so team members can query data without ever seeing passwords), and an immutable activity log that tracks every major action taken across your organization.",
      howItWorksSteps: [
        {
          step: "01",
          title: "Encrypted Credential Storage",
          detail: "Admins save database connection strings in the Vault, where they are protected with AES-256 GCM encryption.",
        },
        {
          step: "02",
          title: "Zero-Knowledge Querying",
          detail: "Team analysts select approved databases from a dropdown to load tables, without ever seeing or copying passwords.",
        },
        {
          step: "03",
          title: "Automated Activity Logging",
          detail: "DataForge automatically logs all key events: file uploads, cleaning rules applied, model tournaments run, and dataset downloads.",
        },
        {
          step: "04",
          title: "Searchable Audit Review",
          detail: "Admins can open the Team Governance drawer anytime to search and review the chronological activity log.",
        },
      ],
      whyUseIt: [
        "Stops password leaks: analysts query corporate databases without raw credentials ever being shared or exposed.",
        "Provides clear accountability: see exactly who made each change, when it occurred, and what data was exported.",
        "Meets regulatory audit requirements for data tracking, compliance, and governance.",
      ],
      useCases: [
        {
          industry: "Corporate Compliance",
          title: "SOC 2 & GDPR Audits",
          description: "Produce detailed chronological activity records showing who accessed and downloaded customer data.",
          icon: ShieldCheck,
        },
        {
          industry: "IT Administration",
          title: "Database Access Control",
          description: "Give teams self-serve access to query read-only databases without distributing database passwords.",
          icon: Database,
        },
      ],
      proTips: [
        "Use the search bar in the Team Governance drawer's Audit tab to quickly filter events by user email or action type.",
      ],
    },
  ];

  // Grouped Navigation Structure
  const navSections: NavSection[] = [
    {
      id: "getting-started",
      title: "Getting Started",
      icon: Compass,
      subItems: [
        { id: "quickstart", title: "Quickstart Guide" },
        { id: "architecture", title: "Core Architecture & Engine" },
      ],
    },
    {
      id: "cleaning",
      title: "Data Cleaning Engine",
      icon: Sparkles,
      badge: "CORE",
      subItems: [
        { id: "cleaning-auto", title: "1-Click Auto Cleaning", badge: "AUTO" },
        { id: "cleaning-dynamic", title: "Dynamic Interactive Cleaning", badge: "RULES" },
        { id: "cleaning-diff", title: "Diff Engine & Python Export" },
      ],
    },
    {
      id: "reports-eda",
      title: "Exploratory EDA & Reports",
      icon: LineChart,
      badge: "UPDATED",
      subItems: [
        { id: "eda-statistical", title: "Statistical Profile" },
        { id: "eda-biz-report", title: "AI Business Analyst Report", badge: "BIZ" },
        { id: "eda-deck", title: "5-Slide Executive Deck", badge: "PRINT" },
        { id: "eda-charts", title: "Visual Chart Studio" },
      ],
    },
    {
      id: "ingestion",
      title: "Data Ingestion Hub",
      icon: Database,
      subItems: [
        { id: "ingestion-local", title: "Local Files (CSV, Excel, Parquet)" },
        { id: "ingestion-sheets", title: "Cloud Google Sheets & Excel Online" },
        { id: "ingestion-vault", title: "Database Connection Vault" },
      ],
    },
    {
      id: "joins",
      title: "Relational Join Studio",
      icon: Layers,
      subItems: [
        { id: "joins-canvas", title: "Visual Join Canvas" },
        { id: "joins-engine", title: "DuckDB In-Memory Merging" },
      ],
    },
    {
      id: "automl",
      title: "AutoML Intelligence",
      icon: Cpu,
      subItems: [
        { id: "automl-tournament", title: "AutoML Model Tournament" },
        { id: "automl-evaluation", title: "Evaluation & Feature Importance" },
        { id: "automl-docker", title: "Production Docker Deployment" },
      ],
    },
    {
      id: "ai-analyst",
      title: "AI Multi-Agent Intelligence",
      icon: Bot,
      badge: "6 AGENTS",
      subItems: [
        {
          id: "ai-chat",
          title: "Natural Language Query Engine",
          badge: "6 AGENTS",
          children: [
            { id: "ai-orchestrator", title: "SupervisorAgent (Chief Analyst)", badge: "CORE" },
            { id: "ai-agent-cleaner", title: "CleanerAgent (Sanitization & Undo)", badge: "AGENT" },
            { id: "ai-agent-automl", title: "AutoMLAgent (Predictive Advisor)", badge: "AGENT" },
            { id: "ai-agent-pipeline", title: "PipelineAgent (Airflow & dbt)", badge: "AGENT" },
            { id: "ai-agent-analytics", title: "AnalyticsAgent (Sandboxed Math)", badge: "AGENT" },
            { id: "ai-agent-visualizer", title: "VisualizerAgent (Chart.js Engine)", badge: "AGENT" },
          ],
        },
        { id: "ai-sessions", title: "Session Management & History" },
      ],
    },
    {
      id: "exports",
      title: "Production Exports",
      icon: Download,
      subItems: [
        { id: "exports-datasets", title: "Multi-Format Dataset Downloads" },
        { id: "exports-pipeline", title: "Pipeline Code & dbt Models" },
        { id: "exports-deck-pdf", title: "Executive Decks & PDF Export" },
      ],
    },
    {
      id: "governance",
      title: "Deployment & Governance",
      icon: ShieldCheck,
      badge: "SECURITY",
      subItems: [
        { id: "governance-roles", title: "3-Tier Roles & Permissions" },
        { id: "governance-sharing", title: "Dataset Sharing & Link Access" },
        { id: "governance-security", title: "OWASP Security & Framing" },
        { id: "governance-vault", title: "Shared Database Vault & Audits" },
      ],
    },
  ];

  // Active Article Lookup
  const currentArticle = useMemo(() => {
    return articles.find((a) => a.id === activeArticleId) || articles[0];
  }, [articles, activeArticleId]);

  // Next / Previous Navigation
  const currentIndex = articles.findIndex((a) => a.id === activeArticleId);
  const prevArticle = currentIndex > 0 ? articles[currentIndex - 1] : null;
  const nextArticle = currentIndex < articles.length - 1 ? articles[currentIndex + 1] : null;

  // Auto-expand section containing active article
  useEffect(() => {
    const parentSection = navSections.find((sec) =>
      sec.subItems?.some(
        (sub) =>
          sub.id === activeArticleId ||
          sub.children?.some((child) => child.id === activeArticleId)
      )
    );
    if (parentSection && !openSections[parentSection.id]) {
      setOpenSections((prev) => ({ ...prev, [parentSection.id]: true }));
    }
  }, [activeArticleId]);

  // Copy helper
  const copyToClipboard = (text: string, key: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedCodeKey(key);
      setTimeout(() => setCopiedCodeKey(null), 2000);
    }
  };

  // Keyboard shortcut Ctrl+K focus search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        const searchInput = document.getElementById("shadcn-doc-search");
        if (searchInput) searchInput.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Filtered search results
  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    return articles.filter(
      (a) =>
        a.title.toLowerCase().includes(q) ||
        a.description.toLowerCase().includes(q) ||
        a.whatItIs.toLowerCase().includes(q) ||
        a.categoryTitle.toLowerCase().includes(q)
    );
  }, [articles, searchQuery]);

  return (
    <div
      className="min-h-screen flex flex-col transition-colors duration-300 relative selection:bg-[var(--accent)] selection:text-white"
      style={{ background: "var(--bg)", color: "var(--txt)" }}
    >
      {/* Top Header */}
      <Header
        onLoginClick={() => setLoginModalOpen(true)}
        onLaunchWorkspace={() => setLaunchModalOpen(true)}
      />

      {/* Dynamic Keyframes for Illuminated Tree Fiber-Optic Lights & Smooth Transitions */}
      <style>{`
        @keyframes docPulseGlow {
          0%, 100% { opacity: 0.35; transform: scale(1); }
          50% { opacity: 0.95; transform: scale(1.15); }
        }
        @keyframes docsTracerFlow {
          from { stroke-dashoffset: 24; }
          to { stroke-dashoffset: 0; }
        }
        .docs-tracer-light {
          animation: docsTracerFlow 1.6s linear infinite;
        }
      `}</style>

      {/* Mobile Sticky Docs Sub-Header with Hamburger Menu */}
      <div
        className="md:hidden sticky top-16 z-30 w-full px-4 py-2.5 flex items-center justify-between border-b backdrop-blur-xl transition-all"
        style={{
          background: "var(--nav)",
          borderColor: "var(--border)",
        }}
      >
        {/* Hamburger Menu Toggle Button for Docs Sidebar */}
        <button
          type="button"
          onClick={() => setMobileSidebarOpen(true)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer active:scale-95 shadow-sm"
          style={{
            borderColor: "var(--border)",
            background: "var(--surface)",
            color: "var(--txt)",
          }}
          aria-label="Open Documentation Sidebar Navigation"
        >
          <Menu size={15} style={{ color: "var(--accent)" }} />
          <span>Docs Menu</span>
        </button>

        {/* Current Article Breadcrumb Badge */}
        <div className="flex items-center gap-1.5 text-xs truncate max-w-[48%]" style={{ color: "var(--txt-m)" }}>
          <span className="truncate font-medium">{currentArticle.title}</span>
        </div>

        {/* Quick Search Focus Button */}
        <button
          type="button"
          onClick={() => {
            setMobileSidebarOpen(true);
            setTimeout(() => {
              document.getElementById("shadcn-doc-search")?.focus();
            }, 100);
          }}
          className="p-1.5 rounded-xl border transition-colors cursor-pointer active:scale-95"
          style={{
            borderColor: "var(--border)",
            background: "var(--surface)",
            color: "var(--txt-m)",
          }}
          aria-label="Search documentation"
        >
          <Search size={15} />
        </button>
      </div>

      {/* Backdrop Overlay for Mobile Sidebar Drawer */}
      {mobileSidebarOpen && (
        <div
          className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300"
          onClick={() => setMobileSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Docs Layout Container */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 flex items-start gap-8 py-8 relative">
        {/* Mobile Sidebar Floating Quick Action Button */}
        <div className="md:hidden fixed bottom-6 right-6 z-40">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
            className="w-12 h-12 rounded-full shadow-2xl text-white flex items-center justify-center border border-white/20 cursor-pointer transition-transform active:scale-90"
            style={{ background: "var(--accent)", boxShadow: "0 4px 20px var(--glow)" }}
            aria-label="Toggle Documentation Navigation"
          >
            {mobileSidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* ── Left Sidebar Navigation (Illuminated Tree Hierarchy) ─────────── */}
        <aside
          className={`fixed md:sticky top-0 md:top-20 z-50 md:z-30 h-screen md:h-[calc(100vh-5.5rem)] w-[85vw] max-w-[320px] md:w-72 shrink-0 overflow-y-auto p-5 md:p-0 md:pr-3 border-r bg-[var(--surface)] md:bg-transparent transition-transform md:transition-none duration-300 ease-out ${
            mobileSidebarOpen
              ? "translate-x-0 shadow-2xl left-0"
              : "-translate-x-full md:translate-x-0 -left-full md:left-0"
          }`}
          style={{
            borderColor: "var(--border)",
          }}
        >
          {/* Mobile Drawer Header with Close Button */}
          <div
            className="flex items-center justify-between pb-4 mb-4 border-b md:hidden"
            style={{ borderColor: "var(--border)" }}
          >
            <div className="flex items-center gap-2.5">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center font-bold text-white shadow-sm"
                style={{ background: "var(--accent)" }}
              >
                <BookOpen size={15} />
              </div>
              <div>
                <span className="text-sm font-bold block leading-none" style={{ color: "var(--txt)" }}>Documentation</span>
                <span className="text-[10px] font-mono leading-none mt-1 block" style={{ color: "var(--txt-m)" }}>Index & Navigation</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(false)}
              className="p-1.5 rounded-lg border transition-colors cursor-pointer hover:bg-white/5 active:scale-95"
              style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
              aria-label="Close Documentation Sidebar"
            >
              <X size={16} />
            </button>
          </div>

          {/* Quick Search Input */}
          <div className="relative mb-5">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--txt-m)" }} />
            <input
              id="shadcn-doc-search"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search docs... (Ctrl+K)"
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border text-xs outline-none transition-all shadow-sm focus:ring-1"
              style={{
                borderColor: "var(--border)",
                background: "var(--surface)",
                color: "var(--txt)",
              }}
            />
          </div>

          {/* Search Dropdown Results */}
          {searchQuery && (
            <div
              className="mb-6 p-2 rounded-xl border text-xs space-y-1"
              style={{ borderColor: "var(--border)", background: "var(--surface)" }}
            >
              <p className="text-[10px] uppercase font-bold px-2 py-1" style={{ color: "var(--txt-m)" }}>Search Results:</p>
              {searchResults.length === 0 ? (
                <p className="px-2 py-1.5 text-xs" style={{ color: "var(--txt-m)" }}>No matching pages.</p>
              ) : (
                searchResults.map((res) => (
                  <button
                    key={res.id}
                    onClick={() => {
                      setActiveArticleId(res.id);
                      setSearchQuery("");
                      setMobileSidebarOpen(false);
                    }}
                    className="w-full text-left px-2 py-1.5 rounded-md flex items-center justify-between transition-colors cursor-pointer"
                    style={{ color: "var(--txt)" }}
                  >
                    <span className="font-semibold truncate">{res.title}</span>
                    <span className="text-[10px] shrink-0" style={{ color: "var(--txt-m)" }}>{res.categoryTitle}</span>
                  </button>
                ))
              )}
            </div>
          )}

          {/* ── Tree-Style Navigation Links (Curved branch SVG with Illuminated Active Tracer) ── */}
          <nav className="space-y-1.5 text-xs">
            {navSections.map((sec) => {
              const SecIcon = sec.icon;
              const hasSubItems = sec.subItems && sec.subItems.length > 0;
              const isOpen = !!openSections[sec.id];
              const isSectionActive =
                sec.subItems?.some((sub) => sub.id === activeArticleId) ||
                sec.id === activeArticleId;

              return (
                <div key={sec.id} className="space-y-0.5">
                  {/* Parent Section Header Button */}
                  <button
                    type="button"
                    onClick={() => {
                      if (hasSubItems) {
                        toggleSection(sec.id);
                      } else {
                        setActiveArticleId(sec.id);
                        setMobileSidebarOpen(false);
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }
                    }}
                    className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer group text-left"
                    style={{
                      background: isSectionActive && !hasSubItems ? "var(--surface)" : "transparent",
                      color: isSectionActive ? "var(--txt)" : "var(--txt-m)",
                      border: isSectionActive && !hasSubItems ? "1px solid var(--accent)" : "1px solid transparent",
                      boxShadow: isSectionActive && !hasSubItems ? "0 0 12px var(--glow)" : "none",
                    }}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <div
                        className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 transition-colors"
                        style={{
                          background: isSectionActive ? "var(--accent)" : "var(--surface)",
                          color: isSectionActive ? "#fff" : "var(--txt-m)",
                          border: isSectionActive ? "none" : "1px solid var(--border)",
                          boxShadow: isSectionActive ? "0 0 10px var(--glow)" : "none",
                        }}
                      >
                        <SecIcon size={13} />
                      </div>
                      <span className="truncate">{sec.title}</span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {sec.badge && (
                        <span
                          className="text-[9px] font-mono px-1.5 py-0.2 rounded-md font-bold uppercase tracking-wider"
                          style={{
                            background: isSectionActive ? "var(--glow)" : "var(--surface)",
                            color: isSectionActive ? "var(--accent)" : "var(--txt-m)",
                            border: isSectionActive ? "1px solid var(--accent)" : "1px solid var(--border)",
                          }}
                        >
                          {sec.badge}
                        </span>
                      )}
                      {hasSubItems && (
                        <span style={{ color: "var(--txt-m)" }}>
                          {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                        </span>
                      )}
                    </div>
                  </button>

                  {/* ── Sub-Items Tree Branch (Synchronized Guide Rails with Illuminated Active Connectors) ── */}
                  {hasSubItems && isOpen && (
                    <div className="relative ml-4 pl-4 my-1.5 space-y-1">
                      {/* Main vertical tree rail connecting all primary sub-items */}
                      <div
                        className="absolute left-[7px] top-0 bottom-2 w-px pointer-events-none transition-colors"
                        style={{ background: isSectionActive ? "var(--border)" : "var(--border)" }}
                      />

                      {sec.subItems!.map((sub) => {
                        const isSubActive = sub.id === activeArticleId;
                        const hasChildren = !!(sub.children && sub.children.length > 0);
                        const isChildActive = hasChildren && sub.children!.some((c) => c.id === activeArticleId);
                        const isSubOrChildActive = isSubActive || isChildActive;

                        return (
                          <div key={sub.id} className="relative space-y-1">
                            {/* Primary Sub-Item Row */}
                            <div className="relative flex items-center group pl-1">
                              {/* Horizontal branch pin connecting from main rail */}
                              <div
                                className="absolute -left-[9px] top-1/2 -translate-y-1/2 w-2.5 h-px pointer-events-none transition-colors"
                                style={{
                                  background: isSubOrChildActive ? "var(--accent)" : "var(--border)",
                                }}
                              />

                              {/* Primary Sub-Item Pill Button */}
                              <button
                                type="button"
                                onClick={() => {
                                  setActiveArticleId(sub.id);
                                  setMobileSidebarOpen(false);
                                  window.scrollTo({ top: 0, behavior: "smooth" });
                                }}
                                className="w-full text-left py-1.5 px-3 rounded-lg text-xs transition-all flex items-center justify-between cursor-pointer group-hover:translate-x-0.5"
                                style={{
                                  background: isSubActive ? "var(--surface)" : isChildActive ? "var(--glow)" : "transparent",
                                  color: isSubActive ? "var(--accent)" : isChildActive ? "var(--txt)" : "var(--txt-m)",
                                  border: isSubActive ? "1px solid var(--accent)" : "1px solid transparent",
                                  boxShadow: isSubActive ? "0 0 16px var(--glow)" : "none",
                                  fontWeight: isSubActive ? 700 : isChildActive ? 600 : 500,
                                }}
                              >
                                <span className="truncate">{sub.title}</span>
                                {sub.badge && (
                                  <span
                                    className="text-[8px] font-mono px-1 py-0.2 rounded font-bold uppercase tracking-wider shrink-0"
                                    style={{
                                      background: isSubActive ? "var(--glow)" : "var(--surface)",
                                      color: isSubActive ? "var(--accent)" : "var(--txt-m)",
                                      border: isSubActive ? "1px solid var(--accent)" : "1px solid var(--border)",
                                    }}
                                  >
                                    {sub.badge}
                                  </span>
                                )}
                              </button>
                            </div>

                            {/* Nested Sub-Headings (Agents indented under Natural Language Query Engine) */}
                            {hasChildren && (
                              <div className="relative ml-4 pl-3.5 my-1 space-y-1">
                                {/* Sub-heading branch vertical rail */}
                                <div
                                  className="absolute left-[6px] top-0 bottom-2 w-px pointer-events-none transition-colors"
                                  style={{
                                    background: isChildActive ? "var(--accent)" : "var(--border)",
                                    boxShadow: isChildActive ? "0 0 8px var(--glow)" : "none",
                                  }}
                                />

                                {sub.children!.map((child) => {
                                  const isThisChildActive = child.id === activeArticleId;

                                  return (
                                    <div key={child.id} className="relative flex items-center group">
                                      {/* Horizontal branch pin connecting from child rail */}
                                      <div
                                        className="absolute -left-[8px] top-1/2 -translate-y-1/2 w-2 h-px pointer-events-none transition-colors"
                                        style={{
                                          background: isThisChildActive ? "var(--accent)" : "var(--border)",
                                        }}
                                      />

                                      {/* Child Agent Pill Button */}
                                      <button
                                        type="button"
                                        onClick={() => {
                                          setActiveArticleId(child.id);
                                          setMobileSidebarOpen(false);
                                          window.scrollTo({ top: 0, behavior: "smooth" });
                                        }}
                                        className="w-full text-left py-1.5 px-2.5 rounded-lg text-xs transition-all flex items-center justify-between cursor-pointer group-hover:translate-x-0.5"
                                        style={{
                                          background: isThisChildActive ? "var(--surface)" : "transparent",
                                          color: isThisChildActive ? "var(--accent)" : "var(--txt-m)",
                                          border: isThisChildActive ? "1px solid var(--accent)" : "1px solid transparent",
                                          boxShadow: isThisChildActive ? "0 0 14px var(--glow)" : "none",
                                          fontWeight: isThisChildActive ? 700 : 500,
                                        }}
                                      >
                                        <span className="truncate">{child.title}</span>
                                        {child.badge && (
                                          <span
                                            className="text-[8px] font-mono px-1 py-0.2 rounded font-bold uppercase tracking-wider shrink-0"
                                            style={{
                                              background: isThisChildActive ? "var(--glow)" : "var(--surface)",
                                              color: isThisChildActive ? "var(--accent)" : "var(--txt-m)",
                                              border: isThisChildActive ? "1px solid var(--accent)" : "1px solid var(--border)",
                                            }}
                                          >
                                            {child.badge}
                                          </span>
                                        )}
                                      </button>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </nav>

          {/* Sidebar Launch Workspace CTA */}
          <div
            className="mt-8 p-3 rounded-2xl border text-xs"
            style={{ borderColor: "var(--border)", background: "var(--surface)" }}
          >
            <p className="font-bold mb-1" style={{ color: "var(--txt)" }}>Try In Your Browser</p>
            <p className="text-[11px] leading-relaxed mb-3" style={{ color: "var(--txt-m)" }}>
              Test dynamic cleaning, statistical profiling, and AutoML with pre-loaded sample datasets.
            </p>
            <button
              onClick={() => setLaunchModalOpen(true)}
              className="w-full py-2 px-3 rounded-lg text-xs font-bold text-white transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-sm active:scale-98"
              style={{ background: "var(--accent)", boxShadow: "0 2px 10px var(--glow)" }}
            >
              <span>Launch Workspace</span>
              <ArrowRight size={12} />
            </button>
          </div>
        </aside>

        {/* ── Main Documentation Article (Center Pane) ───────────────────────── */}
        <main className="flex-1 min-w-0 max-w-3xl pb-16">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-1.5 text-xs mb-4 flex-wrap" style={{ color: "var(--txt-m)" }}>
            <Link href="/" className="hover:underline transition-colors" style={{ color: "var(--txt-m)" }}>
              Docs
            </Link>
            {currentArticle.breadcrumb ? (
              currentArticle.breadcrumb.split(" > ").map((crumb, idx, arr) => (
                <React.Fragment key={idx}>
                  <ChevronRight size={12} />
                  {idx === arr.length - 1 ? (
                    <span className="font-semibold" style={{ color: "var(--accent)" }}>{crumb}</span>
                  ) : (
                    <span>{crumb}</span>
                  )}
                </React.Fragment>
              ))
            ) : (
              <>
                <ChevronRight size={12} />
                <span>{currentArticle.categoryTitle}</span>
                <ChevronRight size={12} />
                <span className="font-semibold" style={{ color: "var(--accent)" }}>{currentArticle.title}</span>
              </>
            )}
          </div>

          {/* Article Header */}
          <div className="mb-8 pb-6 border-b" style={{ borderColor: "var(--border)" }}>
            <div className="flex items-center gap-2 mb-2">
              <span
                className="text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full font-mono transition-all"
                style={{
                  background: "var(--glow)",
                  color: "var(--accent)",
                  border: "1px solid var(--accent)",
                }}
              >
                {currentArticle.badge || "GUIDE"}
              </span>
              <span className="text-xs font-mono" style={{ color: "var(--txt-m)" }}>{currentArticle.categoryTitle}</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-3" style={{ color: "var(--txt)" }}>
              {currentArticle.title}
            </h1>
            <p className="text-sm sm:text-base leading-relaxed" style={{ color: "var(--txt-m)" }}>
              {currentArticle.description}
            </p>

            {/* Quick Action Buttons */}
            <div className="flex items-center gap-3 mt-5">
              <button
                onClick={() => setLaunchModalOpen(true)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-white transition-all flex items-center gap-2 cursor-pointer shadow-sm active:scale-98"
                style={{ background: "var(--accent)", boxShadow: "0 2px 12px var(--glow)" }}
              >
                <Play size={12} fill="currentColor" />
                <span>Open in Workspace</span>
              </button>
              <button
                onClick={() => copyToClipboard(window.location.href, "page-url")}
                className="px-3.5 py-2 rounded-xl text-xs font-medium border transition-all flex items-center gap-1.5 cursor-pointer active:scale-98"
                style={{
                  borderColor: "var(--border)",
                  background: "var(--surface)",
                  color: "var(--txt)",
                }}
              >
                {copiedCodeKey === "page-url" ? <Check size={12} style={{ color: "var(--accent)" }} /> : <Share2 size={12} />}
                <span>{copiedCodeKey === "page-url" ? "Copied Link" : "Share Guide"}</span>
              </button>
            </div>
          </div>

          {/* Team Note Callout Banner (Synchronized with Theme Accent) */}
          {currentArticle.callout && (
            <div
              className="mb-8 p-4 rounded-2xl border flex items-start gap-3.5 text-xs leading-relaxed transition-all"
              style={{
                background: "var(--surface)",
                borderColor: "var(--accent)",
                boxShadow: "0 0 16px var(--glow)",
              }}
            >
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                style={{
                  background: "var(--glow)",
                  color: "var(--accent)",
                  border: "1px solid var(--accent)",
                }}
              >
                <Sparkles size={14} />
              </div>
              <div>
                <h4 className="font-bold text-xs mb-1" style={{ color: "var(--txt)" }}>
                  {currentArticle.callout.title}
                </h4>
                <p style={{ color: "var(--txt-m)" }}>{currentArticle.callout.text}</p>
              </div>
            </div>
          )}

          {/* Section 1: Overview */}
          <section id="what-it-is" className="mb-10">
            <h2
              className="text-xl font-bold tracking-tight mb-3 pb-2 border-b"
              style={{ color: "var(--txt)", borderColor: "var(--border)" }}
            >
              What is this?
            </h2>
            <p className="text-sm leading-relaxed" style={{ color: "var(--txt)" }}>
              {currentArticle.whatItIs}
            </p>
          </section>

          {/* Section 2: Step-by-Step Guide: What to Do */}
          <section id="how-it-works" className="mb-10">
            <h2
              className="text-xl font-bold tracking-tight mb-4 pb-2 border-b"
              style={{ color: "var(--txt)", borderColor: "var(--border)" }}
            >
              Step-by-Step Walkthrough
            </h2>
            <div className="relative pl-7 space-y-7">
              {/* Vertical timeline runner line */}
              <div
                className="absolute left-3 top-2 bottom-2 w-[1.5px] rounded-full pointer-events-none"
                style={{
                  background: "linear-gradient(to bottom, var(--accent) 0%, var(--border) 100%)",
                }}
              />

              {currentArticle.howItWorksSteps.map((st, i) => (
                <div key={i} className="relative group">
                  <div
                    className="absolute -left-7 top-0 w-6 h-6 rounded-full font-mono text-[10px] font-bold flex items-center justify-center transition-all"
                    style={{
                      background: "var(--surface)",
                      color: "var(--accent)",
                      border: "1px solid var(--accent)",
                      boxShadow: "0 0 10px var(--glow)",
                    }}
                  >
                    {st.step}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold mb-1" style={{ color: "var(--txt)" }}>{st.title}</h3>
                    <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>{st.detail}</p>

                    {st.codeSnippet && (
                      <div
                        className="mt-3 rounded-xl border p-3 font-mono text-xs transition-all"
                        style={{
                          borderColor: "var(--border)",
                          background: "var(--surface)",
                        }}
                      >
                        <div
                          className="flex items-center justify-between pb-2 mb-2 border-b text-[10px]"
                          style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                        >
                          <span>{st.codeLang || "bash"}</span>
                          <button
                            onClick={() => copyToClipboard(st.codeSnippet!, `step-${i}`)}
                            className="flex items-center gap-1 cursor-pointer hover:underline"
                            style={{ color: "var(--accent)" }}
                          >
                            {copiedCodeKey === `step-${i}` ? <Check size={11} /> : <Copy size={11} />}
                            <span>{copiedCodeKey === `step-${i}` ? "Copied" : "Copy"}</span>
                          </button>
                        </div>
                        <pre className="overflow-x-auto text-[11px]" style={{ color: "var(--txt)" }}>
                          <code>{st.codeSnippet}</code>
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Code Example (if available) */}
          {currentArticle.codeExample && (
            <section id="code-example" className="mb-10">
              <h2
                className="text-xl font-bold tracking-tight mb-3 pb-2 border-b"
                style={{ color: "var(--txt)", borderColor: "var(--border)" }}
              >
                Code Reference
              </h2>
              <div
                className="rounded-2xl border overflow-hidden transition-all"
                style={{ borderColor: "var(--border)", background: "var(--surface)" }}
              >
                <div
                  className="px-4 py-2 border-b flex items-center justify-between text-xs"
                  style={{
                    borderColor: "var(--border)",
                    background: "var(--inp-bg)",
                    color: "var(--txt-m)",
                  }}
                >
                  <span className="font-mono text-[11px] font-semibold">{currentArticle.codeExample.filename}</span>
                  <button
                    onClick={() => copyToClipboard(currentArticle.codeExample!.code, "main-code")}
                    className="flex items-center gap-1.5 transition-colors cursor-pointer"
                    style={{ color: "var(--accent)" }}
                  >
                    {copiedCodeKey === "main-code" ? <Check size={12} /> : <Copy size={12} />}
                    <span className="text-[11px] font-bold">{copiedCodeKey === "main-code" ? "Copied" : "Copy Code"}</span>
                  </button>
                </div>
                <pre className="p-4 overflow-x-auto text-xs font-mono leading-relaxed" style={{ color: "var(--txt)" }}>
                  <code>{currentArticle.codeExample.code}</code>
                </pre>
              </div>
            </section>
          )}

          {/* Section 3: Why You'll Love It (Why Use It - Single Dynamic Theme Accent) */}
          <section id="why-use-it" className="mb-10">
            <h2
              className="text-xl font-bold tracking-tight mb-3 pb-2 border-b"
              style={{ color: "var(--txt)", borderColor: "var(--border)" }}
            >
              Why Use It
            </h2>
            <div className="grid grid-cols-1 gap-2.5">
              {currentArticle.whyUseIt.map((benefit, i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-2xl border flex items-start gap-3 transition-colors"
                  style={{
                    borderColor: "var(--border)",
                    background: "var(--surface)",
                  }}
                >
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center shrink-0 mt-0.5 transition-all"
                    style={{
                      background: "var(--glow)",
                      color: "var(--accent)",
                      border: "1px solid var(--accent)",
                    }}
                  >
                    <Check size={11} strokeWidth={3} />
                  </div>
                  <span className="text-xs leading-relaxed" style={{ color: "var(--txt)" }}>{benefit}</span>
                </div>
              ))}
            </div>
          </section>

          {/* Section 4: Where People Use It (Real-World Use Cases) */}
          <section id="use-cases" className="mb-10">
            <h2
              className="text-xl font-bold tracking-tight mb-3 pb-2 border-b"
              style={{ color: "var(--txt)", borderColor: "var(--border)" }}
            >
              Where It Can Be Used
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {currentArticle.useCases.map((uc, i) => {
                const UcIcon = uc.icon;
                return (
                  <div
                    key={i}
                    className="p-4 rounded-2xl border flex flex-col justify-between transition-all"
                    style={{
                      borderColor: "var(--border)",
                      background: "var(--surface)",
                    }}
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <div
                          className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                          style={{
                            background: "var(--glow)",
                            color: "var(--accent)",
                            border: "1px solid var(--accent)",
                          }}
                        >
                          <UcIcon size={14} />
                        </div>
                        <span className="text-[10px] font-bold uppercase tracking-wider font-mono" style={{ color: "var(--accent)" }}>
                          {uc.industry}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>{uc.title}</h4>
                      <p className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>{uc.description}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          {/* Section 5: Team Pro Tips (Harmonized with Theme Accent) */}
          {currentArticle.proTips && currentArticle.proTips.length > 0 && (
            <section id="pro-tips" className="mb-12">
              <h2
                className="text-xl font-bold tracking-tight mb-3 pb-2 border-b"
                style={{ color: "var(--txt)", borderColor: "var(--border)" }}
              >
                Pro Analyst Tips from Our Team
              </h2>
              <div
                className="p-4 rounded-2xl border transition-all space-y-2.5 text-xs"
                style={{
                  background: "var(--surface)",
                  borderColor: "var(--border)",
                  borderLeft: "4px solid var(--accent)",
                }}
              >
                {currentArticle.proTips.map((tip, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <Lightbulb size={14} className="shrink-0 mt-0.5" style={{ color: "var(--accent)" }} />
                    <span className="leading-relaxed" style={{ color: "var(--txt)" }}>{tip}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Bottom CTA Banner (Compact Variant) */}
          <div className="my-8">
            <CTABanner
              variant="compact"
              title="Test DataForge with your dataset"
              subtitle="Free plan — zero setup, instant automated EDA."
              buttonText="Launch Workspace"
              onAction={() => setLaunchModalOpen(true)}
              secondaryButtonText="Architecture"
              secondaryHref="/#about"
            />
          </div>

          {/* Bottom Next / Prev Navigation */}
          <div className="pt-8 border-t flex flex-col sm:flex-row items-center justify-between gap-4" style={{ borderColor: "var(--border)" }}>
            {prevArticle ? (
              <button
                onClick={() => {
                  setActiveArticleId(prevArticle.id);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="w-full sm:w-1/2 p-4 rounded-2xl border text-left transition-all cursor-pointer group active:scale-98"
                style={{
                  borderColor: "var(--border)",
                  background: "var(--surface)",
                }}
              >
                <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: "var(--txt-m)" }}>
                  <ChevronLeft size={12} className="group-hover:-translate-x-1 transition-transform" />
                  <span>Previous</span>
                </div>
                <h4 className="text-sm font-bold" style={{ color: "var(--txt)" }}>{prevArticle.title}</h4>
              </button>
            ) : (
              <div className="hidden sm:block sm:w-1/2" />
            )}

            {nextArticle ? (
              <button
                onClick={() => {
                  setActiveArticleId(nextArticle.id);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="w-full sm:w-1/2 p-4 rounded-2xl border text-right transition-all cursor-pointer group active:scale-98"
                style={{
                  borderColor: "var(--border)",
                  background: "var(--surface)",
                }}
              >
                <div className="flex items-center justify-end gap-1.5 text-[10px] font-bold uppercase tracking-wider mb-1" style={{ color: "var(--txt-m)" }}>
                  <span>Next</span>
                  <ChevronRight size={12} className="group-hover:translate-x-1 transition-transform" />
                </div>
                <h4 className="text-sm font-bold" style={{ color: "var(--txt)" }}>{nextArticle.title}</h4>
              </button>
            ) : (
              <div className="hidden sm:block sm:w-1/2" />
            )}
          </div>
        </main>

        {/* ── Right Table of Contents (On this page) ────────────────────────── */}
        <aside
          className="sticky top-24 hidden xl:block w-52 shrink-0 h-[calc(100vh-6rem)] overflow-y-auto pl-4 border-l text-xs"
          style={{ borderColor: "var(--border)" }}
        >
          <p className="font-bold text-[11px] uppercase tracking-wider mb-3" style={{ color: "var(--txt)" }}>
            On this page
          </p>
          <nav className="space-y-2" style={{ color: "var(--txt-m)" }}>
            <a
              href="#what-it-is"
              className="block transition-colors hover:underline"
              style={{ color: "var(--txt-m)" }}
            >
              What is this?
            </a>
            <a
              href="#how-it-works"
              className="block transition-colors hover:underline"
              style={{ color: "var(--txt-m)" }}
            >
              Step-by-Step Guide
            </a>
            {currentArticle.codeExample && (
              <a
                href="#code-example"
                className="block transition-colors hover:underline"
                style={{ color: "var(--txt-m)" }}
              >
                Code Reference
              </a>
            )}
            <a
              href="#why-use-it"
              className="block transition-colors hover:underline"
              style={{ color: "var(--txt-m)" }}
            >
              Why Use It
            </a>
            <a
              href="#use-cases"
              className="block transition-colors hover:underline"
              style={{ color: "var(--txt-m)" }}
            >
              Where It Can Be Used
            </a>
            {currentArticle.proTips && currentArticle.proTips.length > 0 && (
              <a
                href="#pro-tips"
                className="block transition-colors hover:underline"
                style={{ color: "var(--txt-m)" }}
              >
                Pro Analyst Tips
              </a>
            )}
          </nav>

          <div
            className="mt-8 pt-6 border-t text-[11px] space-y-2"
            style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
          >
            <Link
              href="/pricing"
              className="flex items-center gap-1.5 transition-colors hover:underline"
              style={{ color: "var(--accent)" }}
            >
              <span>Subscription Specs</span>
              <ExternalLink size={10} />
            </Link>
            <button
              onClick={() => setLaunchModalOpen(true)}
              className="flex items-center gap-1.5 transition-colors cursor-pointer text-left hover:underline"
              style={{ color: "var(--accent)" }}
            >
              <span>Launch Ingestion Hub</span>
              <ExternalLink size={10} />
            </button>
          </div>
        </aside>
      </div>

      {/* Global Ingestion Hub Launch Modal */}
      <WorkspaceLaunchModal
        isOpen={launchModalOpen}
        onClose={() => setLaunchModalOpen(false)}
      />

      {/* Login Modal */}
      {loginModalOpen && (
        <LoginModal onClose={() => setLoginModalOpen(false)} />
      )}

      {/* Site Footer */}
      <Footer />
    </div>
  );
}
