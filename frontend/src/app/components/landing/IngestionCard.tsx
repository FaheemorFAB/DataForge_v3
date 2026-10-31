"use client";

import React, { useState, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import {
  UploadCloud,
  FileSpreadsheet,
  Database,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  RefreshCw,
  Play,
  Layers,
  Sliders,
  ChevronDown,
  Table as TableIcon,
  Code,
  FileCode2,
  Eye,
  Check,
  X,
  Server,
  Zap,
  Clock,
} from "lucide-react";
import { GoogleSheetsLogo, MicrosoftExcelOnlineLogo } from "./DataLogos";

interface IngestionCardProps {
  isLoggedIn: boolean;
  onLoginRequired: () => void;
  isUploading: boolean;
  fileUploaded: boolean;
  fileName: string;
  profile: any;
  errorMsg: string;
  currentUploadId: string | null;
  sourceTab: "csv" | "sheets" | "excel" | "database";
  setSourceTab: (tab: "csv" | "sheets" | "excel" | "database") => void;
  sheetsUrl: string;
  setSheetsUrl: (url: string) => void;
  sheetsError: string;
  isSheetsLoading: boolean;
  loadSheets: () => Promise<void>;
  excelOnlineUrl?: string;
  setExcelOnlineUrl?: (url: string) => void;
  excelOnlineError?: string;
  isExcelOnlineLoading?: boolean;
  loadExcelOnline?: () => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  reset: () => void;
  goToWorkspace: (uploadId?: string | null) => void;

  // Database props
  dbDialect: "postgresql" | "mysql" | "sqlite" | "clickhouse";
  setDbDialect: (dialect: any) => void;
  dbConnStr: string;
  setDbConnStr: (str: string) => void;
  isDbTesting: boolean;
  testDbConnection: () => Promise<void>;
  dbTestResult: { ok: boolean; message: string } | null;
  dbTables: string[];
  selectedDbTable: string;
  setSelectedDbTable: (t: string) => void;
  dbQueryMode: "table" | "sql";
  setDbQueryMode: (m: "table" | "sql") => void;
  dbCustomSql: string;
  setDbCustomSql: (s: string) => void;
  dbLimit: string;
  setDbLimit: (l: string) => void;
  isDbIngesting: boolean;
  ingestDbData: () => Promise<void>;
  dbError: string;
  dbPreview: any;
  isPreviewingDb: boolean;
  previewDbData: () => Promise<void>;
  isDragging: boolean;
  setIsDragging: (d: boolean) => void;
  handleDrop: (e: React.DragEvent) => Promise<void>;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onUpgradePlan?: (planKey: string) => Promise<void>;
}

export type CardVariation = "studio" | "bento" | "wizard";

const DIALECT_OPTIONS = [
  { id: "postgresql", name: "PostgreSQL", badge: "PG", defaultUri: "postgresql://postgres:password@db.project-ref.supabase.co:5432/postgres", color: "#336791" },
  { id: "mysql", name: "MySQL", badge: "MY", defaultUri: "mysql+pymysql://admin:password@mysql.us-east-1.rds.amazonaws.com:3306/mydb", color: "#00758f" },
  { id: "clickhouse", name: "ClickHouse", badge: "CH", defaultUri: "clickhouse+native://default:password@service.us-east-1.clickhouse.cloud:9440/default", color: "#fca311" },
  { id: "sqlite", name: "SQLite", badge: "SQL", defaultUri: "sqlite:///sample.db", color: "#003b57" },
];

interface DbStatusBannerProps {
  testResult: { ok: boolean; message: string } | null;
  error?: string;
  onUpgrade?: (planKey: string) => Promise<void>;
  compact?: boolean;
}

function DbStatusBanner({ testResult, error, onUpgrade, compact }: DbStatusBannerProps) {
  if (testResult?.ok) {
    return (
      <div
        className={`flex items-center gap-1.5 rounded-xl border font-mono transition-all ${
          compact ? "p-1.5 text-[10px] mt-1" : "p-2.5 text-xs mt-1.5"
        }`}
        style={{
          background: "rgba(16, 185, 129, 0.08)",
          borderColor: "rgba(16, 185, 129, 0.3)",
          color: "#34d399",
        }}
      >
        <CheckCircle2 size={compact ? 11 : 13} className="shrink-0 text-emerald-400" />
        <span className="font-semibold leading-tight">{testResult.message || "Database link verified successfully!"}</span>
      </div>
    );
  }

  const msg = (testResult && !testResult.ok ? testResult.message : error) || "";
  if (!msg) return null;

  const isPlanGated =
    msg.toLowerCase().includes("exclusive to team") ||
    msg.toLowerCase().includes("upgrade your organization") ||
    msg.toLowerCase().includes("payment required") ||
    msg.toLowerCase().includes("plan tier") ||
    msg.toLowerCase().includes("upgrade to team");

  return (
    <div
      className={`rounded-xl border font-mono transition-all flex flex-col gap-1.5 ${
        compact ? "p-2 text-[10px] mt-1.5" : "p-2.5 text-xs mt-1.5"
      }`}
      style={{
        background: isPlanGated ? "rgba(245, 158, 11, 0.08)" : "rgba(239, 68, 68, 0.08)",
        borderColor: isPlanGated ? "rgba(245, 158, 11, 0.35)" : "rgba(239, 68, 68, 0.35)",
        color: isPlanGated ? "#fcd34d" : "#fca5a5",
      }}
    >
      <div className="flex items-start gap-1.5">
        <span className="font-bold shrink-0">{isPlanGated ? "🔒 Plan Locked:" : "✗ Error:"}</span>
        <span className="leading-snug break-words flex-1">{msg}</span>
      </div>

      {isPlanGated && (
        <div className="flex items-center gap-2 pt-0.5">
          {onUpgrade ? (
            <button
              type="button"
              onClick={() => onUpgrade("team")}
              className="px-2.5 py-1 rounded-lg text-[10px] font-bold text-black transition-all hover:scale-[1.02] cursor-pointer flex items-center gap-1 shadow-sm"
              style={{ background: "linear-gradient(135deg, #f59e0b, #fbbf24)" }}
            >
              <Zap size={10} />
              <span>Upgrade to Team Plan</span>
            </button>
          ) : (
            <a
              href="/pricing"
              className="px-2.5 py-1 rounded-lg text-[10px] font-bold text-black transition-all hover:scale-[1.02] cursor-pointer inline-flex items-center gap-1 shadow-sm"
              style={{ background: "linear-gradient(135deg, #f59e0b, #fbbf24)" }}
            >
              <span>View Pricing & Upgrade</span>
              <ArrowRight size={10} />
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default function IngestionCard(props: IngestionCardProps) {
  const [variation, setVariation] = useState<CardVariation>("studio");
  const [wizardStep, setWizardStep] = useState<1 | 2>(1);
  const [loadingSampleId, setLoadingSampleId] = useState<string | null>(null);
  const [showPreviewDrawer, setShowPreviewDrawer] = useState(false);
  const [recentDatasets, setRecentDatasets] = useState<Array<{ id: string; filename: string; rows?: number; cols?: number }>>([]);

  // Load Ingestion History scoped to active workspace (Only if user is logged in)
  useEffect(() => {
    if (!props.isLoggedIn) {
      setRecentDatasets([]);
      return;
    }
    const fetchRecent = async () => {
      try {
        const wsId = (typeof window !== "undefined" && localStorage.getItem("df_active_workspace")) || "personal";
        const res = await apiFetch(`/dashboard/init?workspace_id=${encodeURIComponent(wsId)}`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.recent_uploads)) {
            setRecentDatasets(data.recent_uploads);
          }
        }
      } catch {
        // silent
      }
    };
    fetchRecent();
  }, [props.isLoggedIn]);

  return (
    <div className="w-full relative">
      {/* ── Top Subtle Variation Switcher Bar ────────────────────────────── */}
      <div className="flex items-center justify-between mb-3 px-1 text-xs">
        <div className="flex items-center gap-1.5 opacity-80">
          <Sliders size={12} style={{ color: "var(--accent)" }} />
          <span className="text-[10px] font-mono font-semibold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
            UI Layout:
          </span>
        </div>

        <div
          className="flex items-center gap-1 p-0.5 rounded-lg border backdrop-blur-md"
          style={{
            background: "rgba(255, 255, 255, 0.03)",
            borderColor: "var(--border)",
          }}
        >
          {[
            { id: "studio", label: "Studio (Recommended)", icon: "✨" },
            { id: "bento", label: "Compact Bento", icon: "🍱" },
            { id: "wizard", label: "2-Step Wizard", icon: "⚡" },
          ].map((v) => (
            <button
              key={v.id}
              onClick={() => {
                setVariation(v.id as CardVariation);
                if (v.id === "wizard") setWizardStep(1);
              }}
              className={`px-2.5 py-1 rounded-md text-[10px] font-medium transition-all duration-200 ${
                variation === v.id
                  ? "bg-white/10 text-white shadow-sm font-semibold border border-white/10"
                  : "text-[color:var(--txt-m)] hover:text-white"
              }`}
            >
              <span>{v.icon} </span>
              <span>{v.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Ingestion Container ─────────────────────────────────────── */}
      <div
        className={`relative rounded-2xl p-[1px] transition-all duration-300 ${
          props.isDragging ? "ring-2 ring-orange-500 shadow-2xl scale-[1.01]" : ""
        }`}
        style={{
          background: props.isDragging
            ? "linear-gradient(135deg, var(--accent), #6366f1)"
            : "linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03))",
        }}
      >
        <div
          className="relative rounded-2xl p-6 sm:p-7 backdrop-blur-2xl transition-all"
          style={{
            background: "var(--card)",
            boxShadow: "0 24px 60px -15px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08)",
          }}
          onDragOver={(e) => { e.preventDefault(); props.setIsDragging(true); }}
          onDragLeave={(e) => { e.preventDefault(); props.setIsDragging(false); }}
          onDrop={props.handleDrop}
        >
          {/* Error Banner */}
          {props.errorMsg && (
            <div
              className="mb-4 flex items-center gap-2 p-3 rounded-xl text-xs font-mono text-red-400 border animate-shake"
              style={{ background: "rgba(239, 68, 68, 0.08)", borderColor: "rgba(239, 68, 68, 0.25)" }}
            >
              <X size={15} className="flex-shrink-0" />
              <span className="flex-1">{props.errorMsg}</span>
            </div>
          )}

          {/* Uploading State */}
          {props.isUploading && (
            <div className="py-16 flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative">
                <div
                  className="w-14 h-14 rounded-full border-2 border-t-transparent animate-spin"
                  style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}
                />
                <Sparkles size={18} className="absolute inset-0 m-auto animate-pulse" style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <p className="font-bold text-base" style={{ color: "var(--txt)" }}>Forging dataset...</p>
                <p className="text-xs font-mono mt-1 opacity-70" style={{ color: "var(--txt-m)" }}>{props.fileName}</p>
              </div>
            </div>
          )}

          {/* Uploaded Dataset Success Profile */}
          {props.fileUploaded && !props.isUploading && (
            <div className="w-full space-y-5 text-left">
              <div
                className="flex items-center justify-between p-4 rounded-xl border"
                style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold text-xs shadow-md"
                    style={{ background: "var(--accent)" }}
                  >
                    {props.sourceTab === "sheets" ? "GS" : props.sourceTab === "excel" ? "XLS" : props.sourceTab === "database" ? "SQL" : "CSV"}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <CheckCircle2 size={14} className="text-emerald-400" />
                      <p className="font-bold text-sm truncate max-w-[200px]" style={{ color: "var(--txt)" }}>
                        {props.fileName}
                      </p>
                    </div>
                    <p className="text-[10px] font-mono uppercase tracking-wider mt-0.5" style={{ color: "var(--txt-m)" }}>
                      Dataset Ingested & Profiled
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={props.reset}
                  className="p-1.5 rounded-lg border hover:bg-white/5 transition-all text-xs"
                  style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                  title="Reset"
                >
                  <RefreshCw size={14} />
                </button>
              </div>

              {props.profile && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-3 rounded-xl border text-center" style={{ background: "rgba(255, 255, 255, 0.03)", borderColor: "var(--border)" }}>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Rows</p>
                    <p className="text-lg font-black tracking-tight mt-0.5" style={{ color: "var(--txt)" }}>{props.profile.rows?.toLocaleString()}</p>
                  </div>
                  <div className="p-3 rounded-xl border text-center" style={{ background: "rgba(255, 255, 255, 0.03)", borderColor: "var(--border)" }}>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Columns</p>
                    <p className="text-lg font-black tracking-tight mt-0.5" style={{ color: "var(--txt)" }}>{props.profile.cols}</p>
                  </div>
                  <div className="p-3 rounded-xl border text-center" style={{ background: "rgba(255, 255, 255, 0.03)", borderColor: "var(--border)" }}>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Numeric</p>
                    <p className="text-lg font-black tracking-tight mt-0.5" style={{ color: "var(--txt)" }}>{props.profile.numeric}</p>
                  </div>
                  <div className="p-3 rounded-xl border text-center" style={{ background: "rgba(255, 255, 255, 0.03)", borderColor: "var(--border)" }}>
                    <p className="text-[9px] font-mono font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Null Rate</p>
                    <p className="text-lg font-black tracking-tight mt-0.5" style={{ color: "var(--txt)" }}>{props.profile.missing_pct}%</p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => props.goToWorkspace(props.currentUploadId)}
                  className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl font-bold text-xs text-white shadow-lg transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
                  style={{ background: "linear-gradient(135deg, var(--accent), #ff7043)" }}
                >
                  <Sparkles size={14} />
                  <span>LAUNCH WORKSPACE</span>
                </button>
                <button
                  type="button"
                  onClick={props.reset}
                  className="py-3 px-4 rounded-xl font-bold text-xs border transition-all hover:bg-white/5 text-center"
                  style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                >
                  CHANGE DATASET
                </button>
              </div>
            </div>
          )}

          {/* Active Ingestion Panels (When not yet uploaded) */}
          {!props.fileUploaded && !props.isUploading && (
            <div className="space-y-5">
              <input type="file" accept=".csv" ref={props.fileInputRef} className="hidden" onChange={props.handleFileSelect} />

              {/* ── Segmented Navigation (Sleek, Non-Harsh) ──────────────── */}
              <div
                className="flex p-1 rounded-xl border backdrop-blur-md"
                style={{ background: "rgba(255, 255, 255, 0.03)", borderColor: "var(--border)" }}
              >
                {[
                  { id: "csv", label: "CSV / Local", icon: UploadCloud },
                  { id: "sheets", label: "Google Sheets", icon: FileSpreadsheet },
                  { id: "excel", label: "Excel Online", icon: TableIcon },
                  { id: "database", label: "SQL Database", icon: Database },
                ].map((tab) => {
                  const Icon = tab.icon;
                  const isActive = props.sourceTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => props.setSourceTab(tab.id as any)}
                      className={`flex-1 flex items-center justify-center gap-2 py-2 px-2.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                        isActive
                          ? "bg-white/10 text-white shadow-sm border border-white/15"
                          : "text-[color:var(--txt-m)] hover:text-white"
                      }`}
                      style={
                        isActive
                          ? {
                              background: "rgba(255, 67, 16, 0.12)",
                              borderColor: "rgba(255, 67, 16, 0.35)",
                              color: "var(--txt)",
                            }
                          : {}
                      }
                    >
                      <Icon size={14} style={isActive ? { color: "var(--accent)" } : {}} />
                      <span>{tab.label}</span>
                    </button>
                  );
                })}
              </div>

              {/* ── SOURCE 1: CSV FILE VIEW (Unified Across Variations) ─────── */}
              {props.sourceTab === "csv" && (
                <div className="space-y-4">
                  <div
                    onClick={() => props.fileInputRef.current?.click()}
                    className="cursor-pointer group relative border border-dashed rounded-xl p-8 sm:p-10 flex flex-col items-center justify-center text-center transition-all duration-300 hover:border-orange-500/50 hover:bg-white/[0.015]"
                    style={{
                      borderColor: props.isDragging ? "var(--accent)" : "rgba(255, 255, 255, 0.12)",
                      background: "rgba(255, 255, 255, 0.02)",
                    }}
                  >
                    <div
                      className="w-14 h-14 rounded-2xl flex items-center justify-center mb-3.5 transition-transform duration-300 group-hover:scale-110 shadow-lg border"
                      style={{
                        background: "rgba(255, 67, 16, 0.08)",
                        borderColor: "rgba(255, 67, 16, 0.25)",
                      }}
                    >
                      <UploadCloud size={24} style={{ color: "var(--accent)" }} />
                    </div>

                    <h3 className="text-sm sm:text-base font-bold tracking-tight mb-1" style={{ color: "var(--txt)" }}>
                      Drop your CSV file here
                    </h3>
                    <p className="text-xs max-w-xs mb-3" style={{ color: "var(--txt-m)" }}>
                      Drag & drop or <span className="underline font-semibold" style={{ color: "var(--accent)" }}>browse from computer</span>
                    </p>

                    <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider opacity-60">
                      <span>Max 200 MB</span>
                      <span>•</span>
                      <span>Auto-cleaning & profiling included</span>
                    </div>
                  </div>

                  {/* Dynamic Ingestion History (Hidden completely if user is not logged in) */}
                  {props.isLoggedIn && recentDatasets.length > 0 && (
                    <div className="pt-2 flex items-center justify-between text-xs animate-in fade-in">
                      <span className="text-[10px] font-mono uppercase tracking-wider opacity-60 flex items-center gap-1" style={{ color: "var(--txt-m)" }}>
                        <Clock size={11} style={{ color: "var(--accent)" }} />
                        <span>Recent:</span>
                      </span>
                      <div className="flex gap-1.5 flex-wrap">
                        {recentDatasets.slice(0, 3).map((ds) => (
                          <button
                            key={ds.id}
                            type="button"
                            onClick={() => props.goToWorkspace(ds.id)}
                            className="px-2.5 py-1 rounded-md text-[11px] font-medium border transition-all hover:border-[var(--accent)] hover:bg-white/5 active:scale-95 cursor-pointer max-w-[130px] truncate"
                            style={{
                              background: "rgba(255, 255, 255, 0.03)",
                              borderColor: "var(--border)",
                              color: "var(--txt)",
                            }}
                            title={`Reopen ${ds.filename}`}
                          >
                            <span className="truncate">{ds.filename}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── SOURCE 2: GOOGLE SHEETS VIEW ───────────────────────────── */}
              {props.sourceTab === "sheets" && (
                <div className="space-y-4 text-left">
                  <div
                    className="p-3.5 rounded-xl border flex items-start gap-2.5 text-xs"
                    style={{
                      background: "rgba(99, 102, 241, 0.05)",
                      borderColor: "rgba(99, 102, 241, 0.2)",
                      color: "var(--txt-m)",
                    }}
                  >
                    <FileSpreadsheet size={16} className="text-indigo-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-white">Public Sheet Link Required</p>
                      <p className="text-[11px] opacity-80 mt-0.5">
                        In Sheets, click <strong className="text-white">Share → Anyone with the link can view</strong>.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-mono font-bold uppercase tracking-wider block" style={{ color: "var(--txt-m)" }}>
                      Google Sheets URL
                    </label>
                    <input
                      type="url"
                      value={props.sheetsUrl}
                      onChange={(e) => props.setSheetsUrl(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") props.loadSheets(); }}
                      placeholder="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5..."
                      className="w-full px-3.5 py-2.5 rounded-xl text-xs font-mono outline-none border transition-all focus:ring-1 focus:ring-orange-500"
                      style={{
                        background: "rgba(255, 255, 255, 0.04)",
                        borderColor: props.sheetsError ? "rgba(239, 68, 68, 0.5)" : "var(--border)",
                        color: "var(--txt)",
                      }}
                    />
                    {props.sheetsError && <p className="text-[11px] font-mono text-red-400 mt-1">{props.sheetsError}</p>}
                  </div>

                  <button
                    type="button"
                    onClick={props.loadSheets}
                    disabled={!props.sheetsUrl.trim() || props.isSheetsLoading}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-xs text-white transition-all shadow-md hover:scale-[1.01]"
                    style={{
                      background: props.sheetsUrl.trim() ? "linear-gradient(135deg, var(--accent), #ff7043)" : "rgba(255, 255, 255, 0.08)",
                      opacity: props.sheetsUrl.trim() ? 1 : 0.5,
                      cursor: props.sheetsUrl.trim() ? "pointer" : "not-allowed",
                    }}
                  >
                    {props.isSheetsLoading ? <RefreshCw size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                    <span>{props.isSheetsLoading ? "Importing Sheet..." : "Ingest into DataForge"}</span>
                  </button>
                </div>
              )}

              {/* ── SOURCE 2B: MICROSOFT EXCEL ONLINE VIEW ────────────────────── */}
              {props.sourceTab === "excel" && (
                <div className="space-y-4 text-left">
                  <div
                    className="p-3.5 rounded-xl border flex items-start gap-2.5 text-xs"
                    style={{
                      background: "rgba(16, 124, 65, 0.08)",
                      borderColor: "rgba(16, 124, 65, 0.3)",
                      color: "var(--txt-m)",
                    }}
                  >
                    <MicrosoftExcelOnlineLogo size={20} className="flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-white">OneDrive & SharePoint Workbook Link</p>
                      <p className="text-[11px] opacity-80 mt-0.5">
                        Supports OneDrive (<strong className="text-white">1drv.ms</strong>), SharePoint (<strong className="text-white">sharepoint.com</strong>), and Office 365 cloud sheets. Ensure sharing is set to <strong className="text-white">Anyone with the link can view</strong>.
                      </p>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-mono font-bold uppercase tracking-wider block" style={{ color: "var(--txt-m)" }}>
                      Microsoft Excel Online URL
                    </label>
                    <input
                      type="url"
                      value={props.excelOnlineUrl || ""}
                      onChange={(e) => props.setExcelOnlineUrl?.(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") props.loadExcelOnline?.(); }}
                      placeholder="https://1drv.ms/x/s!Ak... or https://tenant.sharepoint.com/:x:/..."
                      className="w-full px-3.5 py-2.5 rounded-xl text-xs font-mono outline-none border transition-all focus:ring-1 focus:ring-emerald-500"
                      style={{
                        background: "rgba(255, 255, 255, 0.04)",
                        borderColor: props.excelOnlineError ? "rgba(239, 68, 68, 0.5)" : "var(--border)",
                        color: "var(--txt)",
                      }}
                    />
                    {props.excelOnlineError && <p className="text-[11px] font-mono text-red-400 mt-1">{props.excelOnlineError}</p>}
                  </div>

                  <button
                    type="button"
                    onClick={props.loadExcelOnline}
                    disabled={!props.excelOnlineUrl?.trim() || props.isExcelOnlineLoading}
                    className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-xs text-white transition-all shadow-md hover:scale-[1.01]"
                    style={{
                      background: props.excelOnlineUrl?.trim() ? "linear-gradient(135deg, #107C41, #15803d)" : "rgba(255, 255, 255, 0.08)",
                      opacity: props.excelOnlineUrl?.trim() ? 1 : 0.5,
                      cursor: props.excelOnlineUrl?.trim() ? "pointer" : "not-allowed",
                    }}
                  >
                    {props.isExcelOnlineLoading ? <RefreshCw size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                    <span>{props.isExcelOnlineLoading ? "Connecting to Excel Online..." : "Ingest Excel Workbook"}</span>
                  </button>
                </div>
              )}


              {/* ── SOURCE 3: SQL DATABASE (VARIATION-SPECIFIC VIEWS) ────────── */}
              {props.sourceTab === "database" && (
                <>
                  {/* ──────────────────────────────────────────────────────────
                      VARIATION A: "STUDIO" (Spacious, Integrated, Sleek)
                      ────────────────────────────────────────────────────────── */}
                  {variation === "studio" && (
                    <div className="space-y-4 text-left">
                      {/* Compact Dialect Selector */}
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-mono font-bold uppercase tracking-widest block opacity-70" style={{ color: "var(--txt-m)" }}>
                          Select Engine Dialect
                        </label>
                        <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
                          {DIALECT_OPTIONS.map((d) => {
                            const isSelected = props.dbDialect === d.id;
                            return (
                              <button
                                key={d.id}
                                type="button"
                                onClick={() => {
                                  props.setDbDialect(d.id);
                                  props.setDbConnStr(d.defaultUri);
                                }}
                                className={`py-1.5 px-2 rounded-lg text-[10px] font-mono font-medium transition-all border ${
                                  isSelected
                                    ? "bg-white/10 text-white font-bold border-white/20 shadow-sm"
                                    : "text-[color:var(--txt-m)] hover:text-white hover:bg-white/5 border-transparent"
                                }`}
                                style={
                                  isSelected
                                    ? {
                                        background: "rgba(255, 67, 16, 0.12)",
                                        borderColor: "rgba(255, 67, 16, 0.35)",
                                        color: "var(--txt)",
                                      }
                                    : {}
                                }
                              >
                                {d.name}
                              </button>
                            );
                          })}
                        </div>
                      </div>

                      {/* Integrated Connection URI Input with Inline Test Button */}
                      <div className="space-y-1">
                        <label className="text-[10px] font-mono font-bold uppercase tracking-widest block opacity-70" style={{ color: "var(--txt-m)" }}>
                          Connection String (SQLAlchemy URI)
                        </label>
                        <div
                          className="relative flex items-center rounded-xl border transition-all focus-within:border-orange-500/50"
                          style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)" }}
                        >
                          <input
                            type="text"
                            value={props.dbConnStr}
                            onChange={(e) => props.setDbConnStr(e.target.value)}
                            placeholder="postgresql://user:pass@host:5432/db"
                            className="w-full pl-3.5 pr-28 py-2.5 rounded-xl text-xs font-mono outline-none bg-transparent"
                            style={{ color: "var(--txt)" }}
                          />
                          <button
                            type="button"
                            onClick={props.testDbConnection}
                            disabled={!props.dbConnStr.trim() || props.isDbTesting}
                            className="absolute right-1.5 px-2.5 py-1.5 rounded-lg text-[10px] font-mono font-semibold transition-all flex items-center gap-1 border"
                            style={{
                              background: props.dbTestResult?.ok
                                ? "rgba(16, 185, 129, 0.15)"
                                : props.dbTestResult && !props.dbTestResult.ok
                                ? "rgba(239, 68, 68, 0.15)"
                                : "rgba(255, 255, 255, 0.08)",
                              borderColor: props.dbTestResult?.ok
                                ? "rgba(16, 185, 129, 0.4)"
                                : props.dbTestResult && !props.dbTestResult.ok
                                ? "rgba(239, 68, 68, 0.4)"
                                : "var(--border)",
                              color: props.dbTestResult?.ok
                                ? "#10b981"
                                : props.dbTestResult && !props.dbTestResult.ok
                                ? "#ef4444"
                                : "var(--txt)",
                            }}
                          >
                            {props.isDbTesting ? (
                              <RefreshCw size={10} className="animate-spin" />
                            ) : props.dbTestResult?.ok ? (
                              <Check size={11} className="text-emerald-400" />
                            ) : props.dbTestResult && !props.dbTestResult.ok ? (
                              <X size={11} className="text-red-400" />
                            ) : null}
                            <span>
                              {props.isDbTesting
                                ? "Testing..."
                                : props.dbTestResult?.ok
                                ? "Connected"
                                : props.dbTestResult && !props.dbTestResult.ok
                                ? "Failed"
                                : "Test Link"}
                            </span>
                          </button>
                        </div>
                        <DbStatusBanner
                          testResult={props.dbTestResult}
                          error={props.dbError}
                          onUpgrade={props.onUpgradePlan}
                        />
                      </div>

                      {/* Side-by-Side Target Config: Mode + Limit */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-0.5">
                        <div className="space-y-1">
                          <div className="flex items-center justify-between">
                            <label className="text-[10px] font-mono font-bold uppercase tracking-widest opacity-70" style={{ color: "var(--txt-m)" }}>
                              Target Mode
                            </label>
                            <div className="flex gap-1 text-[9px] font-mono">
                              <button
                                type="button"
                                onClick={() => props.setDbQueryMode("table")}
                                className={`px-2 py-0.5 rounded ${
                                  props.dbQueryMode === "table"
                                    ? "bg-white/10 text-white font-bold"
                                    : "opacity-60 hover:opacity-100"
                                }`}
                              >
                                Table
                              </button>
                              <button
                                type="button"
                                onClick={() => props.setDbQueryMode("sql")}
                                className={`px-2 py-0.5 rounded ${
                                  props.dbQueryMode === "sql"
                                    ? "bg-white/10 text-white font-bold"
                                    : "opacity-60 hover:opacity-100"
                                }`}
                              >
                                SQL
                              </button>
                            </div>
                          </div>

                          {props.dbQueryMode === "table" ? (
                            props.dbTables.length > 0 ? (
                              <select
                                value={props.selectedDbTable}
                                onChange={(e) => props.setSelectedDbTable(e.target.value)}
                                className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                                style={{
                                  background: "rgba(255, 255, 255, 0.04)",
                                  borderColor: "var(--border)",
                                  color: "var(--txt)",
                                }}
                              >
                                {props.dbTables.map((t) => (
                                  <option key={t} value={t}>{t}</option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type="text"
                                value={props.selectedDbTable}
                                onChange={(e) => props.setSelectedDbTable(e.target.value)}
                                placeholder="Enter table name..."
                                className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                                style={{
                                  background: "rgba(255, 255, 255, 0.04)",
                                  borderColor: "var(--border)",
                                  color: "var(--txt)",
                                }}
                              />
                            )
                          ) : (
                            <textarea
                              rows={2}
                              value={props.dbCustomSql}
                              onChange={(e) => props.setDbCustomSql(e.target.value)}
                              placeholder="SELECT * FROM table LIMIT 1000"
                              className="w-full px-3 py-1.5 rounded-xl text-xs font-mono outline-none border"
                              style={{
                                background: "rgba(255, 255, 255, 0.04)",
                                borderColor: "var(--border)",
                                color: "var(--txt)",
                              }}
                            />
                          )}
                        </div>

                        <div className="space-y-1">
                          <label className="text-[10px] font-mono font-bold uppercase tracking-widest opacity-70 block" style={{ color: "var(--txt-m)" }}>
                            Row Limit
                          </label>
                          <select
                            value={props.dbLimit}
                            onChange={(e) => props.setDbLimit(e.target.value)}
                            className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                            style={{
                              background: "rgba(255, 255, 255, 0.04)",
                              borderColor: "var(--border)",
                              color: "var(--txt)",
                            }}
                          >
                            <option value="1000">1,000 rows (Instant)</option>
                            <option value="5000">5,000 rows (Standard)</option>
                            <option value="25000">25,000 rows (Deep Batch)</option>
                            <option value="100000">100,000 rows (Large Extract)</option>
                          </select>
                        </div>
                      </div>

                      {/* Collapsible Sample Preview */}
                      {props.dbPreview && (
                        <div
                          className="p-3 rounded-xl border text-[10px] font-mono space-y-1.5"
                          style={{ background: "rgba(0, 0, 0, 0.35)", borderColor: "var(--border)" }}
                        >
                          <div className="flex items-center justify-between text-emerald-400 font-bold uppercase text-[9px]">
                            <span>Sample Preview ({props.dbPreview.rows?.length} rows):</span>
                            <button
                              type="button"
                              onClick={() => setShowPreviewDrawer(!showPreviewDrawer)}
                              className="text-[9px] underline opacity-80 hover:opacity-100"
                            >
                              {showPreviewDrawer ? "Hide" : "View"}
                            </button>
                          </div>
                          {showPreviewDrawer && (
                            <div className="overflow-x-auto max-h-28">
                              <table className="w-full text-left">
                                <thead>
                                  <tr className="border-b border-white/10 opacity-70">
                                    {props.dbPreview.columns?.map((c: any) => (
                                      <th key={c.name} className="pr-3 pb-1">{c.name}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {props.dbPreview.rows?.slice(0, 3).map((r: any, idx: number) => (
                                    <tr key={idx} className="border-b border-white/5">
                                      {props.dbPreview.columns?.map((c: any) => (
                                        <td key={c.name} className="pr-3 py-1 truncate max-w-[80px]">
                                          {String(r[c.name])}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      )}

                      {props.dbError && <p className="text-[11px] font-mono text-red-400">{props.dbError}</p>}

                      {/* Balanced Action Buttons */}
                      <div className="flex gap-2.5 pt-1">
                        <button
                          type="button"
                          onClick={() => {
                            props.previewDbData();
                            setShowPreviewDrawer(true);
                          }}
                          disabled={props.isPreviewingDb || !props.dbConnStr}
                          className="px-3.5 py-2.5 rounded-xl text-xs font-semibold border transition-all hover:bg-white/5 flex items-center gap-1.5"
                          style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                        >
                          <Eye size={13} className="opacity-70" />
                          <span>{props.isPreviewingDb ? "Previewing..." : "Preview Sample"}</span>
                        </button>
                        <button
                          type="button"
                          onClick={props.ingestDbData}
                          disabled={props.isDbIngesting || !props.dbConnStr}
                          className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold text-white shadow-md transition-all hover:scale-[1.01]"
                          style={{ background: "linear-gradient(135deg, var(--accent), #ff7043)" }}
                        >
                          {props.isDbIngesting && <RefreshCw size={13} className="animate-spin" />}
                          <span>{props.isDbIngesting ? "Syncing Database..." : "Ingest into DataForge"}</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* ──────────────────────────────────────────────────────────
                      VARIATION B: "COMPACT BENTO" (High-Density Power User)
                      ────────────────────────────────────────────────────────── */}
                  {variation === "bento" && (
                    <div className="space-y-3 text-left">
                      {/* Dialect selector in a clean dropdown row */}
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[9px] font-mono font-bold uppercase tracking-wider block opacity-70 mb-1" style={{ color: "var(--txt-m)" }}>
                            Dialect Engine
                          </label>
                          <select
                            value={props.dbDialect}
                            onChange={(e) => {
                              const d = DIALECT_OPTIONS.find((opt) => opt.id === e.target.value);
                              if (d) {
                                props.setDbDialect(d.id);
                                props.setDbConnStr(d.defaultUri);
                              }
                            }}
                            className="w-full px-2.5 py-1.5 rounded-lg text-xs font-mono outline-none border"
                            style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                          >
                            {DIALECT_OPTIONS.map((opt) => (
                              <option key={opt.id} value={opt.id}>{opt.name}</option>
                            ))}
                          </select>
                        </div>

                        <div>
                          <label className="text-[9px] font-mono font-bold uppercase tracking-wider block opacity-70 mb-1" style={{ color: "var(--txt-m)" }}>
                            Row Limit
                          </label>
                          <select
                            value={props.dbLimit}
                            onChange={(e) => props.setDbLimit(e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg text-xs font-mono outline-none border"
                            style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                          >
                            <option value="1000">1,000 rows (Instant)</option>
                            <option value="5000">5,000 rows (Standard)</option>
                            <option value="25000">25,000 rows (Large)</option>
                          </select>
                        </div>
                      </div>

                      {/* Connection String with Test status inline */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <label className="text-[9px] font-mono font-bold uppercase tracking-wider opacity-70" style={{ color: "var(--txt-m)" }}>
                            URI String
                          </label>
                          <button
                            type="button"
                            onClick={props.testDbConnection}
                            disabled={!props.dbConnStr.trim() || props.isDbTesting}
                            className="text-[9px] font-mono underline hover:text-white"
                            style={{
                              color: props.dbTestResult?.ok
                                ? "#10b981"
                                : props.dbTestResult && !props.dbTestResult.ok
                                ? "#ef4444"
                                : "var(--accent)",
                            }}
                          >
                            {props.isDbTesting
                              ? "Testing..."
                              : props.dbTestResult?.ok
                              ? "✓ Link Verified"
                              : props.dbTestResult && !props.dbTestResult.ok
                              ? "✗ Test Failed"
                              : "Test Link"}
                          </button>
                        </div>
                        <input
                          type="text"
                          value={props.dbConnStr}
                          onChange={(e) => props.setDbConnStr(e.target.value)}
                          placeholder="postgresql://user:pass@host:5432/db"
                          className="w-full px-2.5 py-1.5 rounded-lg text-xs font-mono outline-none border"
                          style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                        />
                        <DbStatusBanner
                          testResult={props.dbTestResult}
                          error={props.dbError}
                          onUpgrade={props.onUpgradePlan}
                          compact={true}
                        />
                      </div>

                      {/* Table or Query input */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <label className="text-[9px] font-mono font-bold uppercase tracking-wider opacity-70" style={{ color: "var(--txt-m)" }}>
                            Target Table or SQL
                          </label>
                          <div className="flex gap-1 text-[9px] font-mono">
                            <span
                              onClick={() => props.setDbQueryMode("table")}
                              className={`cursor-pointer px-1 rounded ${props.dbQueryMode === "table" ? "text-white font-bold underline" : "opacity-60"}`}
                            >
                              Table
                            </span>
                            <span className="opacity-30">|</span>
                            <span
                              onClick={() => props.setDbQueryMode("sql")}
                              className={`cursor-pointer px-1 rounded ${props.dbQueryMode === "sql" ? "text-white font-bold underline" : "opacity-60"}`}
                            >
                              SQL
                            </span>
                          </div>
                        </div>

                        {props.dbQueryMode === "table" ? (
                          props.dbTables.length > 0 ? (
                            <select
                              value={props.selectedDbTable}
                              onChange={(e) => props.setSelectedDbTable(e.target.value)}
                              className="w-full px-2.5 py-1.5 rounded-lg text-xs font-mono outline-none border"
                              style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                            >
                              {props.dbTables.map((t) => (
                                <option key={t} value={t}>{t}</option>
                              ))}
                            </select>
                          ) : (
                            <input
                              type="text"
                              value={props.selectedDbTable}
                              onChange={(e) => props.setSelectedDbTable(e.target.value)}
                              placeholder="table name (e.g. customers)"
                              className="w-full px-2.5 py-1.5 rounded-lg text-xs font-mono outline-none border"
                              style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                            />
                          )
                        ) : (
                          <textarea
                            rows={2}
                            value={props.dbCustomSql}
                            onChange={(e) => props.setDbCustomSql(e.target.value)}
                            placeholder="SELECT * FROM table LIMIT 1000"
                            className="w-full px-2.5 py-1 rounded-lg text-xs font-mono outline-none border"
                            style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                          />
                        )}
                      </div>

                      {props.dbError && <p className="text-[10px] font-mono text-red-400">{props.dbError}</p>}

                      {/* Ingest Action Button */}
                      <button
                        type="button"
                        onClick={props.ingestDbData}
                        disabled={props.isDbIngesting || !props.dbConnStr}
                        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold text-white shadow-md transition-all hover:scale-[1.01]"
                        style={{ background: "linear-gradient(135deg, var(--accent), #ff7043)" }}
                      >
                        {props.isDbIngesting ? <RefreshCw size={12} className="animate-spin" /> : <Database size={13} />}
                        <span>{props.isDbIngesting ? "Syncing..." : "Connect & Ingest into DataForge"}</span>
                      </button>
                    </div>
                  )}

                  {/* ──────────────────────────────────────────────────────────
                      VARIATION C: "2-STEP WIZARD" (Completely Uncrowded)
                      ────────────────────────────────────────────────────────── */}
                  {variation === "wizard" && (
                    <div className="space-y-4 text-left">
                      {/* Step Indicator Header */}
                      <div className="flex items-center justify-between pb-1 border-b" style={{ borderColor: "var(--border)" }}>
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold ${
                              wizardStep === 1 ? "bg-orange-500 text-white" : "bg-white/10 text-white/70"
                            }`}
                          >
                            1
                          </span>
                          <span className={`text-xs font-semibold ${wizardStep === 1 ? "text-white" : "opacity-60"}`}>
                            Connection
                          </span>
                        </div>
                        <span className="opacity-30">→</span>
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold ${
                              wizardStep === 2 ? "bg-orange-500 text-white" : "bg-white/10 text-white/70"
                            }`}
                          >
                            2
                          </span>
                          <span className={`text-xs font-semibold ${wizardStep === 2 ? "text-white" : "opacity-60"}`}>
                            Target & Ingest
                          </span>
                        </div>
                      </div>

                      {/* STEP 1: Connection & Dialect */}
                      {wizardStep === 1 && (
                        <div className="space-y-3.5">
                          <div>
                            <label className="text-[10px] font-mono font-bold uppercase tracking-widest block opacity-70 mb-1" style={{ color: "var(--txt-m)" }}>
                              Select Dialect
                            </label>
                            <div className="grid grid-cols-3 gap-1.5">
                              {DIALECT_OPTIONS.map((d) => (
                                <button
                                  key={d.id}
                                  type="button"
                                  onClick={() => {
                                    props.setDbDialect(d.id);
                                    props.setDbConnStr(d.defaultUri);
                                  }}
                                  className={`py-1.5 px-2 rounded-lg text-[10px] font-mono font-medium border text-center transition-all ${
                                    props.dbDialect === d.id
                                      ? "bg-white/10 text-white border-white/20 font-bold"
                                      : "text-[color:var(--txt-m)] hover:text-white border-transparent"
                                  }`}
                                >
                                  {d.name}
                                </button>
                              ))}
                            </div>
                          </div>

                          <div className="space-y-1">
                            <label className="text-[10px] font-mono font-bold uppercase tracking-widest block opacity-70" style={{ color: "var(--txt-m)" }}>
                              SQLAlchemy URI
                            </label>
                            <input
                              type="text"
                              value={props.dbConnStr}
                              onChange={(e) => props.setDbConnStr(e.target.value)}
                              placeholder="postgresql://user:pass@host:5432/db"
                              className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                              style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                            />
                            <DbStatusBanner
                              testResult={props.dbTestResult}
                              error={props.dbError}
                              onUpgrade={props.onUpgradePlan}
                            />
                          </div>

                          <div className="flex gap-2 pt-1">
                            <button
                              type="button"
                              onClick={props.testDbConnection}
                              disabled={!props.dbConnStr.trim() || props.isDbTesting}
                              className="px-3.5 py-2.5 rounded-xl text-xs font-semibold border transition-all hover:bg-white/5"
                              style={{
                                borderColor: props.dbTestResult?.ok
                                  ? "rgba(16, 185, 129, 0.4)"
                                  : props.dbTestResult && !props.dbTestResult.ok
                                  ? "rgba(239, 68, 68, 0.4)"
                                  : "var(--border)",
                                color: props.dbTestResult?.ok
                                  ? "#10b981"
                                  : props.dbTestResult && !props.dbTestResult.ok
                                  ? "#ef4444"
                                  : "var(--txt)",
                              }}
                            >
                              {props.isDbTesting
                                ? "Testing..."
                                : props.dbTestResult?.ok
                                ? "✓ Link Verified"
                                : props.dbTestResult && !props.dbTestResult.ok
                                ? "✗ Test Failed"
                                : "Test Connection"}
                            </button>
                            <button
                              type="button"
                              onClick={() => setWizardStep(2)}
                              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-bold text-white shadow-md transition-all hover:scale-[1.01]"
                              style={{ background: "linear-gradient(135deg, var(--accent), #ff7043)" }}
                            >
                              <span>Next: Configure Query</span>
                              <ArrowRight size={13} />
                            </button>
                          </div>
                        </div>
                      )}

                      {/* STEP 2: Target Table/SQL & Launch */}
                      {wizardStep === 2 && (
                        <div className="space-y-3.5">
                          <div className="flex items-center justify-between">
                            <label className="text-[10px] font-mono font-bold uppercase tracking-widest opacity-70" style={{ color: "var(--txt-m)" }}>
                              Target Table or Custom Query
                            </label>
                            <div className="flex gap-1 text-[9px] font-mono">
                              <button
                                type="button"
                                onClick={() => props.setDbQueryMode("table")}
                                className={`px-2 py-0.5 rounded ${props.dbQueryMode === "table" ? "bg-white/10 text-white font-bold" : "opacity-60"}`}
                              >
                                Table
                              </button>
                              <button
                                type="button"
                                onClick={() => props.setDbQueryMode("sql")}
                                className={`px-2 py-0.5 rounded ${props.dbQueryMode === "sql" ? "bg-white/10 text-white font-bold" : "opacity-60"}`}
                              >
                                SQL Query
                              </button>
                            </div>
                          </div>

                          {props.dbQueryMode === "table" ? (
                            props.dbTables.length > 0 ? (
                              <select
                                value={props.selectedDbTable}
                                onChange={(e) => props.setSelectedDbTable(e.target.value)}
                                className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                                style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                              >
                                {props.dbTables.map((t) => (
                                  <option key={t} value={t}>{t}</option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type="text"
                                value={props.selectedDbTable}
                                onChange={(e) => props.setSelectedDbTable(e.target.value)}
                                placeholder="table name (e.g. customers)"
                                className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                                style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                              />
                            )
                          ) : (
                            <textarea
                              rows={2}
                              value={props.dbCustomSql}
                              onChange={(e) => props.setDbCustomSql(e.target.value)}
                              placeholder="SELECT * FROM table LIMIT 1000"
                              className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                              style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                            />
                          )}

                          <div className="space-y-1">
                            <label className="text-[10px] font-mono font-bold uppercase tracking-widest opacity-70 block" style={{ color: "var(--txt-m)" }}>
                              Row Limit
                            </label>
                            <select
                              value={props.dbLimit}
                              onChange={(e) => props.setDbLimit(e.target.value)}
                              className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none border"
                              style={{ background: "rgba(255, 255, 255, 0.04)", borderColor: "var(--border)", color: "var(--txt)" }}
                            >
                              <option value="1000">1,000 rows (Instant)</option>
                              <option value="5000">5,000 rows (Standard)</option>
                              <option value="25000">25,000 rows (Large)</option>
                            </select>
                          </div>

                          <div className="flex gap-2 pt-1">
                            <button
                              type="button"
                              onClick={() => setWizardStep(1)}
                              className="px-3 py-2.5 rounded-xl text-xs font-semibold border hover:bg-white/5"
                              style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                            >
                              ← Back
                            </button>
                            <button
                              type="button"
                              onClick={props.ingestDbData}
                              disabled={props.isDbIngesting || !props.dbConnStr}
                              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold text-white shadow-md transition-all hover:scale-[1.01]"
                              style={{ background: "linear-gradient(135deg, var(--accent), #ff7043)" }}
                            >
                              {props.isDbIngesting && <RefreshCw size={13} className="animate-spin" />}
                              <span>{props.isDbIngesting ? "Syncing Database..." : "Ingest into DataForge"}</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
