"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import gsap from "gsap";
import ThreeBackground from "./ThreeBackground";
import IngestionCard from "./IngestionCard";
import {
  Sparkles,
  Zap,
  BarChart3,
  Brain,
} from "lucide-react";

interface HeroSectionProps {
  onLoginRequired: () => void;
}

export default function HeroSection({ onLoginRequired }: HeroSectionProps) {
  const router = useRouter();
  const { user } = useAuth();
  const isLoggedIn = !!user;

  // Ingestion state
  const [isDragging, setIsDragging] = useState(false);
  const [fileUploaded, setFileUploaded] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [fileName, setFileName] = useState("");
  const [profile, setProfile] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [currentUploadId, setCurrentUploadId] = useState<string | null>(null);

  const [sourceTab, setSourceTab] = useState<"csv" | "sheets" | "excel" | "database">("csv");
  const [sheetsUrl, setSheetsUrl] = useState("");
  const [sheetsError, setSheetsError] = useState("");
  const [isSheetsLoading, setIsSheetsLoading] = useState(false);

  const [excelOnlineUrl, setExcelOnlineUrl] = useState("");
  const [excelOnlineError, setExcelOnlineError] = useState("");
  const [isExcelOnlineLoading, setIsExcelOnlineLoading] = useState(false);

  // Database connector states
  const [dbDialect, setDbDialect] = useState<"postgresql" | "mysql" | "sqlite" | "snowflake" | "bigquery" | "clickhouse">("postgresql");
  const [dbConnStr, setDbConnStr] = useState("postgresql://postgres:password@db.project-ref.supabase.co:5432/postgres");
  const [isDbTesting, setIsDbTesting] = useState(false);
  const [dbTestResult, setDbTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [dbTables, setDbTables] = useState<string[]>([]);
  const [selectedDbTable, setSelectedDbTable] = useState("");
  const [dbQueryMode, setDbQueryMode] = useState<"table" | "sql">("table");
  const [dbCustomSql, setDbCustomSql] = useState("");
  const [dbLimit, setDbLimit] = useState("5000");
  const [isDbIngesting, setIsDbIngesting] = useState(false);
  const [dbError, setDbError] = useState("");
  const [dbPreview, setDbPreview] = useState<any | null>(null);
  const [isPreviewingDb, setIsPreviewingDb] = useState(false);

  const heroContainerRef = useRef<HTMLDivElement>(null);
  const badgeRef = useRef<HTMLDivElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const subtextRef = useRef<HTMLParagraphElement>(null);
  const pillsRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── GSAP Entrance Timeline ─────────────────────────────────────────────────
  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      if (badgeRef.current) {
        tl.fromTo(badgeRef.current, { opacity: 0, y: -16, scale: 0.95 }, { opacity: 1, y: 0, scale: 1, duration: 0.7 });
      }
      if (headingRef.current) {
        tl.fromTo(headingRef.current, { opacity: 0, y: 28 }, { opacity: 1, y: 0, duration: 0.8 }, "-=0.4");
      }
      if (subtextRef.current) {
        tl.fromTo(subtextRef.current, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.7 }, "-=0.5");
      }
      if (pillsRef.current) {
        tl.fromTo(pillsRef.current, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.6 }, "-=0.4");
      }
      if (cardRef.current) {
        tl.fromTo(cardRef.current, { opacity: 0, y: 35, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.9 }, "-=0.6");
      }
    }, heroContainerRef);

    return () => ctx.revert();
  }, []);

  // ── File Handlers ──────────────────────────────────────────────────────────
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (!isLoggedIn) { onLoginRequired(); return; }
    await uploadFile(file);
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!isLoggedIn) { onLoginRequired(); return; }
    await uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    if (!file.name.endsWith('.csv')) { setErrorMsg('Only CSV files are supported.'); return; }
    setErrorMsg(''); setIsUploading(true); setFileName(file.name);
    const fd = new FormData(); fd.append('file', file);
    try {
      const res = await apiFetch('/upload', { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (res.status === 401 || data.error === 'login_required' || data.detail === 'Authentication required') {
        onLoginRequired(); setIsUploading(false); return;
      }
      if (!res.ok || data.error) { setErrorMsg(data.detail || data.error || 'Upload failed.'); return; }
      setProfile(data.profile);
      setCurrentUploadId(data.upload_id);
      setFileUploaded(true);
    } catch (err: any) {
      setErrorMsg('Network error: ' + err.message);
    } finally {
      setIsUploading(false);
    }
  };

  const goToWorkspace = (uploadId?: string | null) => {
    if (uploadId) {
      router.push(`/workspace?upload_id=${encodeURIComponent(uploadId)}`);
    } else {
      router.push('/workspace');
    }
  };

  const reset = useCallback(() => {
    setFileUploaded(false);
    setFileName('');
    setProfile(null);
    setErrorMsg('');
    setSheetsUrl('');
    setSheetsError('');
    setExcelOnlineUrl('');
    setExcelOnlineError('');
    setDbTestResult(null);
    setDbTables([]);
    setSelectedDbTable('');
    setDbError('');
    setDbPreview(null);
    setCurrentUploadId(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, []);

  const loadSheets = async () => {
    if (!sheetsUrl.trim()) return;
    if (!isLoggedIn) { onLoginRequired(); return; }
    setSheetsError('');
    setIsSheetsLoading(true);
    try {
      const res = await apiFetch('/upload/sheets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: sheetsUrl.trim() }),
      });
      const data = await res.json();
      if (res.status === 401 || data.error === 'login_required') {
        onLoginRequired(); return;
      }
      if (!res.ok || data.error || !data.ok) {
        setSheetsError(data.detail || data.error || 'Import failed.'); return;
      }
      setProfile(data.profile);
      setFileName(data.profile?.filename || 'Google Sheet');
      setCurrentUploadId(data.upload_id);
      setFileUploaded(true);
      goToWorkspace(data.upload_id);
    } catch (err: any) {
      setSheetsError('Network error: ' + err.message);
    } finally {
      setIsSheetsLoading(false);
    }
  };

  const loadExcelOnline = async () => {
    if (!excelOnlineUrl.trim()) return;
    if (!isLoggedIn) { onLoginRequired(); return; }
    setExcelOnlineError('');
    setIsExcelOnlineLoading(true);
    try {
      const res = await apiFetch('/upload/excel-online', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: excelOnlineUrl.trim() }),
      });
      const data = await res.json();
      if (res.status === 401 || data.error === 'login_required') {
        onLoginRequired(); return;
      }
      if (!res.ok || data.error || !data.ok) {
        setExcelOnlineError(data.detail || data.error || 'Import failed.'); return;
      }
      setProfile(data.profile);
      setFileName(data.profile?.filename || 'Excel Online Workbook');
      setCurrentUploadId(data.upload_id);
      setFileUploaded(true);
      goToWorkspace(data.upload_id);
    } catch (err: any) {
      setExcelOnlineError('Network error: ' + err.message);
    } finally {
      setIsExcelOnlineLoading(false);
    }
  };


  // Database connector actions
  const testDbConnection = async () => {
    if (!dbConnStr.trim()) return;
    if (!isLoggedIn) { onLoginRequired(); return; }
    setIsDbTesting(true);
    setDbError("");
    setDbTestResult(null);
    try {
      const res = await apiFetch('/upload/database/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connection_string: dbConnStr.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        const errMsg = data.detail || data.message || `Database test failed (HTTP ${res.status})`;
        setDbTestResult({ ok: false, message: errMsg });
        setDbError(errMsg);
        return;
      }
      setDbTestResult({
        ok: Boolean(data.ok),
        message: data.message || (data.ok ? "Connection successful" : "Database connection failed"),
      });
      if (data.ok) {
        setDbError("");
        loadDbTables();
      } else {
        setDbError(data.message || "Connection test failed.");
      }
    } catch (err: any) {
      const msg = err.message || "Failed to reach database server.";
      setDbTestResult({ ok: false, message: msg });
      setDbError(msg);
    } finally {
      setIsDbTesting(false);
    }
  };

  const loadDbTables = async () => {
    try {
      const res = await apiFetch('/upload/database/tables', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ connection_string: dbConnStr.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        const errMsg = data.detail || data.message || "Failed to load database tables.";
        setDbError(errMsg);
        return;
      }
      if (data.ok && Array.isArray(data.tables)) {
        setDbTables(data.tables);
        if (data.tables.length > 0 && !selectedDbTable) {
          setSelectedDbTable(data.tables[0]);
        }
      }
    } catch (err: any) {
      setDbError(err.message || "Failed to inspect database schema.");
    }
  };

  const handleUpgradePlan = async (targetPlan = "team") => {
    try {
      const res = await apiFetch('/subscription/upgrade', {
        method: 'POST',
        body: JSON.stringify({ plan: targetPlan, direct_apply: true }),
      });
      const data = await res.json();
      if (res.ok && data.ok) {
        setDbError("");
        setDbTestResult(null);
        // Automatically re-test database connection with new entitlements
        testDbConnection();
      } else if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        router.push('/pricing');
      }
    } catch {
      router.push('/pricing');
    }
  };

  const previewDbData = async () => {
    if (!dbConnStr.trim()) return;
    setIsPreviewingDb(true);
    setDbError("");
    try {
      const res = await apiFetch('/upload/database/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_string: dbConnStr.trim(),
          table_name: dbQueryMode === 'table' ? selectedDbTable : undefined,
          query: dbQueryMode === 'sql' ? dbCustomSql.trim() : undefined,
          limit: 10,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Preview failed.");
      setDbPreview(data);
    } catch (err: any) {
      setDbError(err.message || "Preview query failed.");
    } finally {
      setIsPreviewingDb(false);
    }
  };

  const ingestDbData = async () => {
    if (!dbConnStr.trim()) return;
    if (!isLoggedIn) { onLoginRequired(); return; }
    setIsDbIngesting(true);
    setDbError("");
    try {
      const res = await apiFetch('/upload/database/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_string: dbConnStr.trim(),
          table_name: dbQueryMode === 'table' ? selectedDbTable : undefined,
          query: dbQueryMode === 'sql' ? dbCustomSql.trim() : undefined,
          limit: parseInt(dbLimit, 10),
          dataset_name: dbQueryMode === 'table' ? `${selectedDbTable}.csv` : "sql_query.csv",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Database ingestion failed.");
      setProfile(data.profile);
      setFileName(dbQueryMode === 'table' ? selectedDbTable : "SQL Query Result");
      setCurrentUploadId(data.upload_id);
      setFileUploaded(true);
      goToWorkspace(data.upload_id);
    } catch (err: any) {
      setDbError(err.message || "Ingestion failed.");
    } finally {
      setIsDbIngesting(false);
    }
  };

  return (
    <div
      ref={heroContainerRef}
      className="relative w-full min-h-[82vh] flex items-center justify-center py-10 px-4 sm:px-6 lg:px-8 overflow-hidden"
    >
      {/* 3D Interactive Three.js Particle Mesh in Background */}
      <ThreeBackground />

      <div className="relative z-10 w-full max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
        
        {/* Left Column: Minimalist Value Proposition & Typography */}
        <div className="lg:col-span-6 space-y-6 text-left">
          
          {/* Luminous Version Tag */}
          <div ref={badgeRef} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-semibold tracking-wide border backdrop-blur-md transition-all"
            style={{
              background: "rgba(255, 67, 16, 0.06)",
              borderColor: "rgba(255, 67, 16, 0.25)",
              color: "var(--txt)"
            }}>
            <span className="w-2 h-2 rounded-full animate-ping" style={{ background: "var(--accent)" }}></span>
            <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: "var(--accent)" }}>DATAFORGE 2.0</span>
            <span className="opacity-40">/</span>
            <span className="text-[11px] font-medium" style={{ color: "var(--txt-m)" }}>Autonomous Ingestion & AutoML</span>
          </div>

          {/* Headline */}
          <h1
            ref={headingRef}
            className="text-4xl sm:text-5xl lg:text-[3.85rem] font-black leading-[1.04] tracking-tight"
            style={{ color: "var(--txt)" }}
          >
            Turn Raw Data Into <br className="hidden sm:inline" />
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage: "linear-gradient(135deg, var(--accent) 0%, #ff8a65 50%, var(--txt) 100%)",
              }}
            >
              Actionable Clarity.
            </span>
          </h1>

          {/* Subtitle */}
          <p
            ref={subtextRef}
            className="text-base sm:text-lg leading-relaxed font-normal max-w-xl"
            style={{ color: "var(--txt-m)" }}
          >
            Instant auto-cleaning, distribution profiling, AI-powered insights, and multi-model AutoML leaderboards. Zero setup, zero boilerplate.
          </p>

          {/* Quick Pillars */}
          <div ref={pillsRef} className="flex flex-wrap items-center gap-2 pt-2">
            {[
              { icon: Zap, label: "Zero-Config Clean" },
              { icon: BarChart3, label: "Statistical EDA" },
              { icon: Brain, label: "FLAML AutoML" },
              { icon: Sparkles, label: "AI Insights" },
            ].map((p, idx) => {
              const Icon = p.icon;
              return (
                <div
                  key={idx}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-medium border"
                  style={{
                    background: "rgba(255, 255, 255, 0.03)",
                    borderColor: "var(--border)",
                    color: "var(--txt-m)",
                  }}
                >
                  <Icon size={13} style={{ color: "var(--accent)" }} />
                  <span>{p.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Sleek Glassmorphic Ingestion Hub */}
        <div ref={cardRef} className="lg:col-span-6 w-full">
          <IngestionCard
            isLoggedIn={isLoggedIn}
            onLoginRequired={onLoginRequired}
            isUploading={isUploading}
            fileUploaded={fileUploaded}
            fileName={fileName}
            profile={profile}
            errorMsg={errorMsg}
            currentUploadId={currentUploadId}
            sourceTab={sourceTab}
            setSourceTab={setSourceTab}
            sheetsUrl={sheetsUrl}
            setSheetsUrl={setSheetsUrl}
            sheetsError={sheetsError}
            isSheetsLoading={isSheetsLoading}
            loadSheets={loadSheets}
            excelOnlineUrl={excelOnlineUrl}
            setExcelOnlineUrl={setExcelOnlineUrl}
            excelOnlineError={excelOnlineError}
            isExcelOnlineLoading={isExcelOnlineLoading}
            loadExcelOnline={loadExcelOnline}
            uploadFile={uploadFile}

            reset={reset}
            goToWorkspace={goToWorkspace}
            dbDialect={dbDialect}
            setDbDialect={setDbDialect}
            dbConnStr={dbConnStr}
            setDbConnStr={setDbConnStr}
            isDbTesting={isDbTesting}
            testDbConnection={testDbConnection}
            dbTestResult={dbTestResult}
            dbTables={dbTables}
            selectedDbTable={selectedDbTable}
            setSelectedDbTable={setSelectedDbTable}
            dbQueryMode={dbQueryMode}
            setDbQueryMode={setDbQueryMode}
            dbCustomSql={dbCustomSql}
            setDbCustomSql={setDbCustomSql}
            dbLimit={dbLimit}
            setDbLimit={setDbLimit}
            isDbIngesting={isDbIngesting}
            ingestDbData={ingestDbData}
            dbError={dbError}
            dbPreview={dbPreview}
            isPreviewingDb={isPreviewingDb}
            previewDbData={previewDbData}
            isDragging={isDragging}
            setIsDragging={setIsDragging}
            handleDrop={handleDrop}
            handleFileSelect={handleFileSelect}
            fileInputRef={fileInputRef}
            onUpgradePlan={handleUpgradePlan}
          />
        </div>

      </div>
    </div>
  );
}
