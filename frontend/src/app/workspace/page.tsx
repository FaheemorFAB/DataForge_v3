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
import { MultiSheetTab } from "./components/MultiSheetTab";
import { TeamGovernanceDrawer } from "./components/TeamGovernanceDrawer";
import { ModelRegistryTab } from "./components/ModelRegistryTab";
import { PipelineStudioModal } from "./components/PipelineStudioModal";
import ThemeSwitcher from "../components/ThemeSwitcher";
import Logo from "../components/Logo";
import UserMenu from "../components/UserMenu";
import ErrorState from "../components/ErrorState";
import WorkspaceLaunchModal from "../components/landing/WorkspaceLaunchModal";
import ShareModal from "./components/ShareModal";
import { SheetSyncModal } from "./components/SheetSyncModal";
import Spinner from "../components/ui/Spinner";
import { SAMPLE_DATASETS, SampleDataset } from "../components/landing/sampleDatasets";
import { apiFetch } from "@/lib/api";
import {
  Table, GitMerge, Wand2, LayoutDashboard, Lightbulb, MessageSquare,
  FileText, Bot, Database, Boxes, Users, Code, UploadCloud, Sparkles,
  RefreshCw, PlusCircle, CheckCircle2, AlertTriangle, ChevronDown,
  ArrowRight, Zap, MoreHorizontal, FileSpreadsheet,
} from "lucide-react";
import {
  SupabaseLogo, PostgresLogo,
  CSVLogo, ParquetLogo,
} from "../components/landing/DataLogos";

// ── Role Config (Strict 3-Tier Enterprise RBAC)
const ROLES = [
  { id: "Admin",   label: "Admin",   color: "var(--accent)", desc: "Full platform & team governance" },
  { id: "Analyst", label: "Analyst", color: "var(--accent)", desc: "EDA, AutoML, transforms & insights" },
  { id: "Viewer",  label: "Viewer",  color: "var(--txt-m)",  desc: "Read-only dashboards & summaries" },
] as const;
type RoleId = typeof ROLES[number]["id"];

// ── Tab Config
const TABS = [
  { id: "preview",   label: "My Data",     icon: Table,          desc: "View and search your dataset" },
  { id: "cleaning",  label: "Clean & Fix", icon: Wand2,          desc: "Repair blanks and fix data types" },
  { id: "dashboard", label: "Dashboard",   icon: LayoutDashboard,desc: "Executive KPI strip & visual reports" },
  { id: "insights",  label: "Insights",    icon: Lightbulb,      desc: "Key takeaways in plain English" },
  { id: "query",     label: "Ask AI",      icon: MessageSquare,  desc: "Chat with your data naturally" },
  { id: "automl",    label: "AutoML",      icon: Bot,            desc: "Train predictive models with AutoML" },
  { id: "models",    label: "Models",      icon: Boxes,          desc: "Manage trained prediction models" },
  { id: "eda",       label: "Reports",     icon: FileText,       desc: "Export executive briefing deck" },
  { id: "multisheet",label: "Multi-Sheet", icon: FileSpreadsheet,desc: "Multi-table & multi-sheet analytics studio" },
] as const;
type TabId = typeof TABS[number]["id"];

const PRIMARY_TAB_IDS: TabId[] = ["preview", "cleaning", "dashboard", "insights", "query", "automl", "models", "eda", "multisheet"];

function WorkspaceContent() {
  const {
    activeTab, setActiveTab, profile, cleanProfile, apiError, uploadId, shareMeta,
    sourceType, isSyncingSheets, syncSheets, syncModalState, closeSyncModal,
    isLoadingWorkspace,
  } = useWorkspace();

  const [mounted, setMounted] = useState(false);
  const [showIngestModal, setShowIngestModal] = useState(false);
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
    setMounted(true);
    const stored = localStorage.getItem("df_user_role") as RoleId | null;
    if (stored && ROLES.find(r => r.id === stored)) setActiveRole(stored);
  }, []);

  useEffect(() => {
    if (shareMeta?.effective_role) {
      const match = ROLES.find(r => r.id.toLowerCase() === shareMeta.effective_role.toLowerCase());
      if (match) setActiveRole(match.id);
    }
  }, [shareMeta?.effective_role]);

  useEffect(() => {
    if (!mounted) return;
    if (uploadId) {
      setShowIngestModal(false);
    }
  }, [uploadId, mounted]);

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
        className="sticky top-0 z-30 flex items-center justify-between shrink-0 px-2 sm:px-4 h-[52px] border-b gap-1.5 sm:gap-2"
        style={{ background: "var(--nav)", borderColor: "var(--border)" }}
      >
        {/* Left: Logo + dataset pill */}
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <Link href="/" className="flex items-center gap-2 shrink-0 no-underline">
            <Logo size={22} textSize={15} textClassName="hidden sm:flex" />
          </Link>

          {profile ? (
            <>
              <div className="w-px h-4 shrink-0 hidden sm:block" style={{ background: "var(--border)" }} />
              <div
                className="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-2.5 py-1 rounded-lg border text-xs min-w-0 max-w-[190px] sm:max-w-none"
                style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
              >
                {cleanProfile && (
                  <span className="hidden md:inline-flex px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wide shrink-0" style={{ background: "rgba(16,185,129,.15)", color: "#10b981" }}>
                    Cleaned
                  </span>
                )}
                <span className="font-semibold truncate max-w-[70px] xs:max-w-[100px] sm:max-w-[140px] md:max-w-[180px]" style={{ color: "var(--txt)" }}>
                  {profile?.filename ?? "Dataset"}
                </span>
                <span className="hidden md:inline" style={{ color: "var(--border)" }}>·</span>
                <span className="shrink-0 hidden md:inline">{activeRows.toLocaleString()} rows</span>
                <span className="hidden lg:inline" style={{ color: "var(--border)" }}>·</span>
                <span className="shrink-0 hidden lg:inline">{activeCols} cols</span>
                <button
                  onClick={() => { if (!isClean) setActiveTab("cleaning" as any); }}
                  className="flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded text-[10px] font-bold border shrink-0 cursor-pointer"
                  style={{
                    background:  isClean ? "rgba(16,185,129,.1)"  : "rgba(245,158,11,.1)",
                    borderColor: isClean ? "rgba(16,185,129,.3)"  : "rgba(245,158,11,.3)",
                    color:       isClean ? "#10b981"               : "#f59e0b",
                  }}
                  title={isClean ? "Data is clean" : `${missing} blanks — click to fix`}
                >
                  {isClean
                    ? <><CheckCircle2 size={10} /><span className="hidden sm:inline">Clean</span></>
                    : <><AlertTriangle size={10} /><span className="sm:hidden">{missing}</span><span className="hidden sm:inline">{health}% · {missing} blanks</span></>
                  }
                </button>
              </div>

              {/* Prominent Google Sheets Live Sync Button */}
              {sourceType === "sheets" && (
                <button
                  onClick={() => syncSheets()}
                  disabled={isSyncingSheets}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold border transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-sm disabled:opacity-60 shrink-0"
                  style={{
                    background: "rgba(16, 185, 129, 0.12)",
                    borderColor: "rgba(16, 185, 129, 0.35)",
                    color: "#10b981",
                  }}
                  title="Fetch latest updates, added rows, or edits directly from Google Sheets"
                >
                  <RefreshCw size={11} className={isSyncingSheets ? "animate-spin" : ""} />
                  <span className="hidden sm:inline">{isSyncingSheets ? "Syncing..." : "Sync Sheet"}</span>
                  <span className="sm:hidden">{isSyncingSheets ? "..." : "Sync"}</span>
                </button>
              )}
            </>
          ) : (isLoadingWorkspace || !profile) && uploadId && !apiError ? (
            <>
              <div className="w-px h-4 shrink-0 hidden sm:block" style={{ background: "var(--border)" }} />
              <div
                className="flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs min-w-0"
                style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping shrink-0" />
                <span className="font-semibold text-[11px] sm:text-xs truncate" style={{ color: "var(--txt)" }}>
                  Loading dataset...
                </span>
              </div>
            </>
          ) : null}
        </div>

        {/* Right: Role + Share + Overflow + Theme + User */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Pipeline Studio / Make Your Own Pipeline Button (desktop / tablet) */}
          {mounted && uploadId && (
            <button
              onClick={() => setShowPipelineModal(true)}
              className="hidden md:flex items-center gap-1.5 px-2.5 lg:px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer border shadow-sm whitespace-nowrap shrink-0"
              style={{
                background: "rgba(99, 102, 241, 0.12)",
                borderColor: "rgba(99, 102, 241, 0.35)",
                color: "#818cf8",
              }}
              title="Build, automate, and export your custom data pipeline (DF-SPE, dbt, Airflow)"
            >
              <Code size={13} />
              <span className="hidden lg:inline">⚡ Pipeline Studio</span>
              <span className="lg:hidden">Pipeline</span>
            </button>
          )}

          {/* Share Button (Google Sheets Style) */}
          {mounted && uploadId && (
            <button
              onClick={() => setShowShareModal(true)}
              className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg text-xs font-bold transition-all hover:scale-[1.02] active:scale-[0.98] cursor-pointer shadow-sm shrink-0"
              style={{
                background: "var(--accent)",
                color: "#ffffff",
                boxShadow: "0 2px 8px var(--glow)",
              }}
              title="Share dataset and manage access"
            >
              <Users size={13} />
              <span className="hidden sm:inline">Share</span>
            </button>
          )}

          {/* Shared By Badge */}
          {mounted && shareMeta?.is_shared && (
            <div
              className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold shrink-0"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--txt)",
              }}
              title={`Shared by ${shareMeta.owner_name} (${shareMeta.owner_email || ""})`}
            >
              <div
                className="relative w-5 h-5 rounded-full overflow-hidden border shrink-0 flex items-center justify-center text-[10px] font-bold"
                style={{ borderColor: "var(--accent)", background: "var(--glow)" }}
              >
                {shareMeta.owner_avatar ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={shareMeta.owner_avatar}
                    alt={shareMeta.owner_name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.currentTarget as HTMLElement).style.display = "none";
                    }}
                  />
                ) : null}
                <span style={{ color: "var(--accent)" }}>{(shareMeta.owner_name || "O")[0].toUpperCase()}</span>
              </div>
              <span className="text-[11px] font-medium" style={{ color: "var(--txt-m)" }}>Shared by</span>
              <span className="text-[11px] font-bold truncate max-w-[100px]">{shareMeta.owner_name}</span>
            </div>
          )}

          {/* Role Selector */}
          <div className="relative" ref={roleMenuRef}>
            <button
              onClick={() => setShowRoleMenu(!showRoleMenu)}
              className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-lg border text-xs font-semibold cursor-pointer shrink-0"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
              title={`Role: ${currentRole.label}`}
            >
              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: currentRole.color }} />
              <span className="hidden sm:inline" suppressHydrationWarning>{currentRole.label}</span>
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
              className="flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 rounded-lg border cursor-pointer shrink-0"
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
                {/* Mobile Pipeline Studio shortcut */}
                {mounted && uploadId && (
                  <button
                    onClick={() => { setShowPipelineModal(true); setShowOverflow(false); }}
                    className="md:hidden w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs cursor-pointer hover:bg-[var(--row-h)]"
                    style={{ color: "#818cf8" }}
                  >
                    <Code size={13} />
                    <span className="font-medium">⚡ Pipeline Studio</span>
                  </button>
                )}

                {overflowTabs.length > 0 && (
                  <>
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
                  </>
                )}
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

      {/* ══ TAB STRIP ══ */}
      <div
        className="w-full h-[42px] border-b shrink-0 flex items-center px-2 sm:px-3 gap-0.5 overflow-x-auto no-scrollbar no-print"
        style={{ background: "var(--nav)", borderColor: "var(--border)", WebkitOverflowScrolling: "touch" }}
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
              className="relative flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-medium cursor-pointer whitespace-nowrap transition-colors duration-100 shrink-0"
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
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-bold cursor-pointer whitespace-nowrap shrink-0"
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

        <div className="flex-1 min-w-[8px]" />
        {!uploadId && !profile && (
          <button
            onClick={() => setShowIngestModal(true)}
            className="flex items-center gap-1.5 px-2 sm:px-2.5 py-1 rounded-lg text-[11px] font-semibold border cursor-pointer hover:border-[var(--accent)] hover:text-[var(--txt)] transition-all shrink-0"
            style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
            title="Import a new dataset or connect a data source"
          >
            <UploadCloud size={12} style={{ color: "var(--accent)" }} />
            <span className="hidden sm:inline">Import Dataset</span>
            <span className="sm:hidden">Import</span>
          </button>
        )}
      </div>

      {/* ══ MAIN CONTENT ══ */}
      <main className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden">
        {!mounted || (isLoadingWorkspace && !profile) || isLoadingSample || (uploadId && !profile && !apiError) ? (
          <div className="min-h-full flex flex-col items-center justify-center p-8 text-center animate-fadeIn">
            <Spinner
              size="lg"
              variant="brand"
              label={isLoadingSample ? "Mounting Sample Dataset..." : "Mounting Dataset & Workspace..."}
              description="Connecting to columnar engine, calculating schema types, and preparing analytics telemetry..."
            />
          </div>
        ) : (
          <>
            <div className={`workspace-tab-panel ${activeTab === "preview" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "preview"   ? "block" : "none", height: "100%" }}><ExplorerTab /></div>
            <div className={`workspace-tab-panel ${activeTab === "multisheet" || activeTab === "joins" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "multisheet" || activeTab === "joins" ? "block" : "none", height: "100%" }}><MultiSheetTab /></div>
            <div className={`workspace-tab-panel ${activeTab === "cleaning" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "cleaning"  ? "block" : "none", height: "100%" }}><CleanerTab /></div>
            <div className={`workspace-tab-panel ${activeTab === "eda" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "eda"       ? "block" : "none", height: "100%" }}><EDATab /></div>
            <div className={`workspace-tab-panel ${activeTab === "automl" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "automl"    ? "block" : "none", height: "100%" }}><AutoMLTab /></div>
            <div className={`workspace-tab-panel ${activeTab === "models" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "models"    ? "block" : "none", height: "100%" }}><ModelRegistryTab /></div>
            <div className={`workspace-tab-panel ${activeTab === "dashboard" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "dashboard" ? "block" : "none", height: "100%" }}><DashboardTab /></div>
            <div className={`workspace-tab-panel ${activeTab === "insights" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "insights"  ? "block" : "none", height: "100%" }}><InsightsTab /></div>
            <div className={`workspace-tab-panel ${activeTab === "query" ? "workspace-tab-active" : "workspace-tab-hidden hidden"}`} style={{ display: activeTab === "query"     ? "block" : "none", height: "100%" }}><ChatSidebar /></div>
          </>
        )}
      </main>

      <WorkspaceLaunchModal
        isOpen={showIngestModal && !uploadId}
        onClose={() => setShowIngestModal(false)}
        hasActiveDataset={!!(uploadId && profile)}
        activeDatasetName={(cleanProfile || profile)?.filename || "Dataset"}
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
      <SheetSyncModal
        state={syncModalState}
        onClose={closeSyncModal}
        onExplore={() => setActiveTab("preview")}
      />
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
