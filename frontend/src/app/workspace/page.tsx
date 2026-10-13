"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { WorkspaceProvider, useWorkspace } from "./components/WorkspaceProvider";
import { ExplorerTab } from "./components/ExplorerTab";
import { CleanerTab } from "./components/CleanerTab";
import { EDATab } from "./components/EDATab";
import { AutoMLTab } from "./components/AutoMLTab";
import { InsightsTab } from "./components/InsightsTab";
import { ChatSidebar } from "./components/ChatSidebar";
import { DashboardTab } from "./components/DashboardTab";
import { JoinCanvasTab } from "./components/JoinCanvasTab";
import { TeamGovernanceDrawer } from "./components/TeamGovernanceDrawer";
import { ModelRegistryTab } from "./components/ModelRegistryTab";
import { PipelineStudioModal } from "./components/PipelineStudioModal";
import ThemeSwitcher from "../components/ThemeSwitcher";
import Logo from "../components/Logo";
import UserMenu from "../components/UserMenu";
import ErrorState from "../components/ErrorState";
import WorkspaceLaunchModal from "../components/landing/WorkspaceLaunchModal";
import ShareModal from "./components/ShareModal";
import { SAMPLE_DATASETS, SampleDataset } from "../components/landing/sampleDatasets";
import { apiFetch } from "@/lib/api";
import {
  Table, GitMerge, Wand2, LayoutDashboard, Lightbulb, MessageSquare,
  FileText, Bot, Database, Boxes, Users, Code, UploadCloud, Sparkles,
  RefreshCw, PlusCircle, CheckCircle2, AlertTriangle, ChevronDown,
  ArrowRight, Zap, MoreHorizontal,
} from "lucide-react";
import {
  SupabaseLogo, PostgresLogo, SnowflakeLogo, BigQueryLogo,
  CSVLogo, ParquetLogo,
} from "../components/landing/DataLogos";

// ── Role Config
const ROLES = [
  { id: "Admin",         label: "Admin",         color: "#ef4444", desc: "Full platform access" },
  { id: "Data Engineer", label: "Data Engineer", color: "#8b5cf6", desc: "Pipelines & schema design" },
  { id: "Analyst",       label: "Analyst",       color: "#3b82f6", desc: "Insights & dashboards" },
  { id: "Viewer",        label: "Viewer",        color: "#6b7280", desc: "Read-only access" },
] as const;
type RoleId = typeof ROLES[number]["id"];

// ── Tab Config
const TABS = [
  { id: "preview",   label: "My Data",     icon: Table,          desc: "View and search your dataset" },
  { id: "cleaning",  label: "Clean & Fix", icon: Wand2,          desc: "Repair blanks and fix data types" },
  { id: "dashboard", label: "Charts",      icon: LayoutDashboard,desc: "Build charts and visual reports" },
  { id: "insights",  label: "Insights",    icon: Lightbulb,      desc: "Key takeaways in plain English" },
  { id: "query",     label: "Ask AI",      icon: MessageSquare,  desc: "Chat with your data naturally" },
  { id: "automl",    label: "AI Forecast", icon: Bot,            desc: "Predict outcomes with AutoML" },
  { id: "eda",       label: "Reports",     icon: FileText,       desc: "Export executive briefing deck" },
  { id: "joins",     label: "Join Tables", icon: GitMerge,       desc: "Combine datasets with visual joins" },
  { id: "models",    label: "Models",      icon: Boxes,          desc: "Manage trained prediction models" },
] as const;
type TabId = typeof TABS[number]["id"];

const PRIMARY_TAB_IDS: TabId[] = ["preview", "cleaning", "dashboard", "insights", "query", "automl", "eda", "joins"];

function WorkspaceContent() {
  const { activeTab, setActiveTab, profile, cleanProfile, apiError, uploadId } = useWorkspace();

  const [showIngestModal, setShowIngestModal] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const urlUid = new URLSearchParams(window.location.search).get("upload_id");
      return !urlUid && !uploadId;
    }
    return false;
  });
  const [showTeamDrawer, setShowTeamDrawer]   = useState(false);
  const [showPipelineModal, setShowPipelineModal] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [activeRole, setActiveRole] = useState<RoleId>("Analyst");
  const [showRoleMenu, setShowRoleMenu] = useState(false);
  const [showOverflow, setShowOverflow] = useState(false);
  const [isLoadingSample, setIsLoadingSample] = useState(false);
  const roleMenuRef = useRef<HTMLDivElement>(null);
  const overflowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("df_user_role") as RoleId | null;
      if (stored && ROLES.find(r => r.id === stored)) setActiveRole(stored);
    }
  }, []);

  useEffect(() => {
    if (uploadId) {
      setShowIngestModal(false);
    } else {
      const urlUid = typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("upload_id") : null;
      if (!urlUid) setShowIngestModal(true);
    }
  }, [uploadId]);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (roleMenuRef.current && !roleMenuRef.current.contains(e.target as Node)) setShowRoleMenu(false);
      if (overflowRef.current && !overflowRef.current.contains(e.target as Node)) setShowOverflow(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleRoleChange = (role: RoleId) => {
    setActiveRole(role);
    localStorage.setItem("df_user_role", role);
    setShowRoleMenu(false);
  };

  const activeRows = (cleanProfile || profile)?.rows || 0;
  const activeCols = (cleanProfile || profile)?.cols || 0;
  const missing    = (cleanProfile || profile)?.missing || 0;
  const totalCells = activeRows * activeCols || 1;
  const health     = Math.max(0, Math.min(100, Math.round(100 - (missing / totalCells) * 100)));
  const isClean    = !!cleanProfile || missing === 0;

  const primaryTabs  = TABS.filter(t => PRIMARY_TAB_IDS.includes(t.id as TabId));
  const overflowTabs = TABS.filter(t => !PRIMARY_TAB_IDS.includes(t.id as TabId));
  const currentRole  = ROLES.find(r => r.id === activeRole) ?? ROLES[2];

  const handleLaunchSample = async (sample: SampleDataset) => {
    setIsLoadingSample(true);
    try {
      const blob = new Blob([sample.csvContent], { type: "text/csv" });
      const file = new File([blob], sample.filename, { type: "text/csv" });
      const fd = new FormData();
      fd.append("file", file);
      const res = await apiFetch("/upload", { method: "POST", body: fd });
      if (res.ok) {
        const data = await res.json();
        window.location.href = `/workspace?upload_id=${data.upload_id}`;
      }
    } catch (e) { console.error(e); }
    finally { setIsLoadingSample(false); }
  };

  if (apiError) {
    return (
      <div className="flex flex-col h-screen" style={{ background: "var(--bg)", color: "var(--txt)" }}>
        <nav className="flex items-center px-6 h-[52px] border-b" style={{ background: "var(--nav)", borderColor: "var(--border)" }}>
          <Link href="/" className="no-underline"><Logo size={24} textSize={16} /></Link>
        </nav>
        <div className="flex-grow flex items-center justify-center">
          <ErrorState code={apiError.code} message={apiError.message} />
        </div>
      </div>
    );
  }

  const activeOverflowTab = overflowTabs.find(t => t.id === activeTab);

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: "var(--bg)", color: "var(--txt)" }}>

      {/* ══ TOP NAV ══ */}
      <nav
        className="sticky top-0 z-30 flex items-center justify-between shrink-0 px-4 h-[52px] border-b"
        style={{ background: "var(--nav)", borderColor: "var(--border)" }}
      >
        {/* Left: Logo + dataset pill */}
        <div className="flex items-center gap-3 min-w-0">
          <Link href="/" className="flex items-center gap-2 shrink-0 no-underline">
            <Logo size={22} textSize={15} />
          </Link>

          {profile && (
            <>
              <div className="w-px h-4 shrink-0" style={{ background: "var(--border)" }} />
              <div
                className="flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs min-w-0"
                style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
              >
                {cleanProfile && (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide shrink-0" style={{ background: "rgba(16,185,129,.15)", color: "#10b981" }}>
                    Cleaned
                  </span>
                )}
                <span className="font-semibold truncate max-w-[160px]" style={{ color: "var(--txt)" }}>
                  {profile?.filename ?? "Dataset"}
                </span>
                <span style={{ color: "var(--border)" }}>·</span>
                <span className="shrink-0">{activeRows.toLocaleString()} rows</span>
                <span style={{ color: "var(--border)" }}>·</span>
                <span className="shrink-0">{activeCols} cols</span>
                <button
                  onClick={() => { if (!isClean) setActiveTab("cleaning" as any); }}
                  className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold border shrink-0 cursor-pointer"
                  style={{
                    background:  isClean ? "rgba(16,185,129,.1)"  : "rgba(245,158,11,.1)",
                    borderColor: isClean ? "rgba(16,185,129,.3)"  : "rgba(245,158,11,.3)",
                    color:       isClean ? "#10b981"               : "#f59e0b",
                  }}
                  title={isClean ? "Data is clean" : `${missing} blanks — click to fix`}
                >
                  {isClean
                    ? <><CheckCircle2 size={10} /><span>Clean</span></>
                    : <><AlertTriangle size={10} /><span>{health}% · {missing} blanks</span></>
                  }
                </button>
                <button
                  onClick={() => setShowIngestModal(true)}
                  className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium opacity-60 hover:opacity-100 transition-opacity cursor-pointer shrink-0"
                  style={{ color: "var(--accent)" }}
                  title="Switch dataset"
                >
                  <RefreshCw size={10} />
                </button>
              </div>
            </>
          )}
        </div>

        {/* Right: Role + Share + Overflow + Theme + User */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Pipeline Studio / Make Your Own Pipeline Button */}
          {uploadId && (
            <button
              onClick={() => setShowPipelineModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer border shadow-sm"
              style={{
                background: "rgba(99, 102, 241, 0.12)",
                borderColor: "rgba(99, 102, 241, 0.35)",
                color: "#818cf8",
              }}
              title="Build, automate, and export your custom data pipeline (DF-SPE, dbt, Airflow)"
            >
              <Code size={13} />
              <span>⚡ Pipeline Studio</span>
            </button>
          )}

          {/* Share Button (Google Sheets Style) */}
          {uploadId && (
            <button
              onClick={() => setShowShareModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-sm"
              style={{
                background: "var(--accent)",
                color: "#ffffff",
                boxShadow: "0 2px 8px var(--glow)",
              }}
              title="Share dataset and manage access"
            >
              <Users size={13} />
              <span>Share</span>
            </button>
          )}

          {/* Role Selector */}
          <div className="relative" ref={roleMenuRef}>
            <button
              onClick={() => setShowRoleMenu(!showRoleMenu)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
              title="Change your role"
            >
              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: currentRole.color }} />
              <span>{currentRole.label}</span>
              <ChevronDown size={11} style={{ color: "var(--txt-m)" }} />
            </button>
            {showRoleMenu && (
              <div
                className="absolute right-0 mt-1.5 w-56 rounded-xl border p-1.5 shadow-2xl z-50"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-f)" }}>
                  Switch Role
                </p>
                {ROLES.map(role => (
                  <button
                    key={role.id}
                    onClick={() => handleRoleChange(role.id as RoleId)}
                    className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs cursor-pointer hover:bg-[var(--row-h)]"
                    style={{ color: "var(--txt)" }}
                  >
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: role.color }} />
                    <span className="font-semibold flex-1 text-left">{role.label}</span>
                    {activeRole === role.id && <CheckCircle2 size={12} style={{ color: "var(--accent)" }} />}
                    <span className="text-[10px]" style={{ color: "var(--txt-f)" }}>{role.desc}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Overflow / More Tools */}
          <div className="relative" ref={overflowRef}>
            <button
              onClick={() => setShowOverflow(!showOverflow)}
              className="flex items-center justify-center w-8 h-8 rounded-lg border cursor-pointer"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
              title="More tools"
            >
              <MoreHorizontal size={14} />
            </button>
            {showOverflow && (
              <div
                className="absolute right-0 mt-1.5 w-52 rounded-xl border p-1.5 shadow-2xl z-50"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt-f)" }}>
                  More Tools
                </p>
                {overflowTabs.map(tab => {
                  const Icon = tab.icon;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => { setActiveTab(tab.id as any); setShowOverflow(false); }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs cursor-pointer hover:bg-[var(--row-h)]"
                      style={{ color: activeTab === tab.id ? "var(--accent)" : "var(--txt)" }}
                    >
                      <Icon size={13} />
                      <span className="font-medium">{tab.label}</span>
                    </button>
                  );
                })}
                <div className="mx-2 my-1 border-t" style={{ borderColor: "var(--border)" }} />
                <button
                  onClick={() => { setShowPipelineModal(true); setShowOverflow(false); }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs cursor-pointer hover:bg-[var(--row-h)]"
                  style={{ color: "var(--txt)" }}
                >
                  <Code size={13} />
                  <span className="font-medium">Pipeline Studio</span>
                </button>
                <button
                  onClick={() => { setShowTeamDrawer(true); setShowOverflow(false); }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs cursor-pointer hover:bg-[var(--row-h)]"
                  style={{ color: "var(--txt)" }}
                >
                  <Users size={13} />
                  <span className="font-medium">Team & Access</span>
                </button>
              </div>
            )}
          </div>

          <ThemeSwitcher />
          <UserMenu />
        </div>
      </nav>

      {/* ══ TAB STRIP — only shown when data is loaded ══ */}
      {profile && (
        <div
          className="w-full h-[42px] border-b shrink-0 flex items-center px-3 gap-0.5 overflow-x-auto"
          style={{ background: "var(--nav)", borderColor: "var(--border)" }}
        >
          {primaryTabs.map(tab => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            const hasBadge = tab.id === "cleaning" && !isClean && missing > 0;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                title={tab.desc}
                className="relative flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium cursor-pointer whitespace-nowrap transition-colors duration-100"
                style={{
                  background:   isActive ? "var(--glow)" : "transparent",
                  color:        isActive ? "var(--accent)" : "var(--txt-m)",
                  fontWeight:   isActive ? 700 : 500,
                  borderBottom: isActive ? "2px solid var(--accent)" : "2px solid transparent",
                  borderRadius: "8px 8px 0 0",
                }}
              >
                <Icon size={13} />
                <span>{tab.label}</span>
                {hasBadge && (
                  <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full" style={{ background: "#f59e0b" }} />
                )}
              </button>
            );
          })}

          {/* Show active overflow tab in strip */}
          {activeOverflowTab && (
            <button
              onClick={() => setShowOverflow(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold cursor-pointer whitespace-nowrap"
              style={{
                background:   "var(--glow)",
                color:        "var(--accent)",
                borderBottom: "2px solid var(--accent)",
                borderRadius: "8px 8px 0 0",
              }}
            >
              <activeOverflowTab.icon size={13} />
              <span>{activeOverflowTab.label}</span>
            </button>
          )}

          <div className="flex-1" />
          <button
            onClick={() => setShowIngestModal(true)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold border cursor-pointer"
            style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
            title="Add or switch dataset"
          >
            <PlusCircle size={12} style={{ color: "var(--accent)" }} />
            <span>Add Data</span>
          </button>
        </div>
      )}

      {/* ══ MAIN CONTENT ══ */}
      <main className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        {!profile && !uploadId ? (
          /* Launchpad */
          <div className="min-h-full flex flex-col items-center justify-center p-6 md:p-12 relative overflow-hidden">
            <div
              className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] blur-[120px] rounded-full pointer-events-none opacity-25"
              style={{ background: "var(--accent)" }}
            />
            <div className="max-w-3xl w-full mx-auto space-y-8 relative z-10">
              <div className="text-center space-y-3">
                <div
                  className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-bold border"
                  style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}
                >
                  <Zap size={12} />
                  <span>DataForge · Powered by DuckDB</span>
                </div>
                <h1 className="text-3xl md:text-4xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
                  Start by loading your data
                </h1>
                <p className="text-sm max-w-xl mx-auto leading-relaxed" style={{ color: "var(--txt-m)" }}>
                  Upload a file, connect a database, or try a sample dataset. No SQL or coding required.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Card: Database */}
                <button
                  onClick={() => setShowIngestModal(true)}
                  className="p-5 rounded-2xl border text-left cursor-pointer group hover:border-[var(--accent)] hover:scale-[1.01] transition-all flex flex-col gap-4"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center border" style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}>
                      <Database size={18} />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold" style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}>
                      Live Sync
                    </span>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold" style={{ color: "var(--txt)" }}>Database & Warehouse</h3>
                    <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--txt-m)" }}>
                      Connect PostgreSQL, Snowflake, BigQuery, or ClickHouse.
                    </p>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-1.5 opacity-70">
                      <PostgresLogo size={15} /><SupabaseLogo size={15} /><SnowflakeLogo size={15} /><BigQueryLogo size={15} />
                    </div>
                    <span className="text-xs font-bold flex items-center gap-1 group-hover:translate-x-0.5 transition-transform" style={{ color: "var(--accent)" }}>
                      Connect <ArrowRight size={12} />
                    </span>
                  </div>
                </button>

                {/* Card: Files */}
                <button
                  onClick={() => setShowIngestModal(true)}
                  className="p-5 rounded-2xl border text-left cursor-pointer group hover:border-[var(--accent)] hover:scale-[1.01] transition-all flex flex-col gap-4"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center border" style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}>
                      <UploadCloud size={18} />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold" style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}>
                      Drag & Drop
                    </span>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold" style={{ color: "var(--txt)" }}>Upload a File</h3>
                    <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--txt-m)" }}>
                      CSV, Excel, Parquet, or JSON — auto-detected and ready in seconds.
                    </p>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-1.5 opacity-70">
                      <CSVLogo size={15} /><ParquetLogo size={15} />
                    </div>
                    <span className="text-xs font-bold flex items-center gap-1 group-hover:translate-x-0.5 transition-transform" style={{ color: "var(--accent)" }}>
                      Browse <ArrowRight size={12} />
                    </span>
                  </div>
                </button>

                {/* Card: Sample Data */}
                <div className="p-5 rounded-2xl border flex flex-col gap-4" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                  <div className="flex items-center justify-between">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center border" style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}>
                      <Sparkles size={18} />
                    </div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full border font-bold" style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}>
                      Try it now
                    </span>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold" style={{ color: "var(--txt)" }}>Sample Datasets</h3>
                    <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--txt-m)" }}>
                      Explore a pre-loaded dataset with one click.
                    </p>
                  </div>
                  <div className="space-y-1.5">
                    {SAMPLE_DATASETS.slice(0, 2).map(s => (
                      <button
                        key={s.id}
                        onClick={() => handleLaunchSample(s)}
                        disabled={isLoadingSample}
                        className="w-full px-3 py-2 rounded-xl border text-xs font-semibold flex items-center justify-between cursor-pointer disabled:opacity-50 hover:border-[var(--accent)] transition-colors"
                        style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                      >
                        <span className="truncate">{s.name}</span>
                        <ArrowRight size={11} style={{ color: "var(--accent)" }} className="shrink-0 ml-1" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <>
            <div style={{ display: activeTab === "preview"   ? "block" : "none", height: "100%" }}><ExplorerTab /></div>
            <div style={{ display: activeTab === "joins"     ? "block" : "none", height: "100%" }}><JoinCanvasTab /></div>
            <div style={{ display: activeTab === "cleaning"  ? "block" : "none", height: "100%" }}><CleanerTab /></div>
            <div style={{ display: activeTab === "eda"       ? "block" : "none", height: "100%" }}><EDATab /></div>
            <div style={{ display: activeTab === "automl"    ? "block" : "none", height: "100%" }}><AutoMLTab /></div>
            <div style={{ display: activeTab === "models"    ? "block" : "none", height: "100%" }}><ModelRegistryTab /></div>
            <div style={{ display: activeTab === "dashboard" ? "block" : "none", height: "100%" }}><DashboardTab /></div>
            <div style={{ display: activeTab === "insights"  ? "block" : "none", height: "100%" }}><InsightsTab /></div>
            <div style={{ display: activeTab === "query"     ? "block" : "none", height: "100%" }}><ChatSidebar /></div>
          </>
        )}
      </main>

      <WorkspaceLaunchModal
        isOpen={showIngestModal}
        onClose={() => setShowIngestModal(false)}
      />
      <ShareModal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        uploadId={uploadId || ""}
        datasetName={(cleanProfile || profile)?.filename || "Dataset"}
        onRoleChanged={(role) => {
          if (ROLES.find(r => r.id === role)) {
            setActiveRole(role as RoleId);
          }
        }}
      />
      <TeamGovernanceDrawer isOpen={showTeamDrawer} onClose={() => setShowTeamDrawer(false)} />
      <PipelineStudioModal isOpen={showPipelineModal} onClose={() => setShowPipelineModal(false)} uploadId={uploadId || ""} />
    </div>
  );
}

export default function WorkspacePage() {
  return (
    <WorkspaceProvider>
      <WorkspaceContent />
    </WorkspaceProvider>
  );
}
