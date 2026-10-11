"use client";

import React, { useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import Scratch from "../ui/Scratch";

interface HeroSectionProps {
  onLoginRequired: () => void;
}

export default function HeroSection({ onLoginRequired }: HeroSectionProps) {
  const router = useRouter();
  const { user } = useAuth();
  const isLoggedIn = !!user;

  const [isDragging, setIsDragging] = useState(false);
  const [fileUploaded, setFileUploaded] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [fileName, setFileName] = useState("");
  const [profile, setProfile] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [currentUploadId, setCurrentUploadId] = useState<string | null>(null);

  const [sourceTab, setSourceTab] = useState<"csv" | "sheets" | "database">("csv");
  const [sheetsUrl, setSheetsUrl] = useState("");
  const [sheetsError, setSheetsError] = useState("");
  const [isSheetsLoading, setIsSheetsLoading] = useState(false);

  // Database connector states
  const [dbDialect, setDbDialect] = useState<"postgresql" | "mysql" | "sqlite" | "snowflake" | "bigquery" | "clickhouse">("postgresql");
  const [dbConnStr, setDbConnStr] = useState("postgresql://postgres:password@localhost:5432/postgres");
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

  const fileInputRef = useRef<HTMLInputElement>(null);

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
      const data = await res.json();
      if (res.status === 401 || data.error === 'login_required') {
        onLoginRequired(); setIsUploading(false); return;
      }
      if (!res.ok || data.error) { setErrorMsg(data.error || 'Upload failed.'); return; }
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
    setDbTestResult(null);
    setDbTables([]);
    setSelectedDbTable('');
    setDbError('');
    setDbPreview(null);
    setCurrentUploadId(null);
  }, []);

  const loadSheets = async () => {
    if (!sheetsUrl.trim()) return;
    if (!isLoggedIn) { onLoginRequired(); return; }
    setSheetsError('');
    setIsSheetsLoading(true);
    try {
      const res = await apiFetch('/upload/sheets', {
        method: 'POST',
        body: JSON.stringify({ url: sheetsUrl.trim() }),
      });
      const data = await res.json();
      if (res.status === 401 || data.error === 'login_required') {
        onLoginRequired(); return;
      }
      if (!res.ok || data.error) {
        setSheetsError(data.error || 'Import failed.'); return;
      }
      setProfile(data.profile);
      setFileName(data.profile.filename || 'Google Sheet');
      setCurrentUploadId(data.upload_id);
      setFileUploaded(true);
      goToWorkspace(data.upload_id);
    } catch (err: any) {
      setSheetsError('Network error: ' + err.message);
    } finally {
      setIsSheetsLoading(false);
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
      setDbTestResult({ ok: data.ok, message: data.message });
      if (data.ok) {
        // Automatically fetch tables
        loadDbTables();
      }
    } catch (err: any) {
      setDbTestResult({ ok: false, message: err.message || "Failed to reach database server." });
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
      if (data.ok && Array.isArray(data.tables)) {
        setDbTables(data.tables);
        if (data.tables.length > 0 && !selectedDbTable) {
          setSelectedDbTable(data.tables[0]);
        }
      }
    } catch (err) {}
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
    <div className="max-w-6xl w-full mx-auto px-5 md:px-8 grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-center min-h-[75vh] py-12">
      {/* Left Value prop */}
      <div className="lg:col-span-5 space-y-4">
        <div className="space-y-4">
          <h1 className="font-black uppercase leading-[0.92] tracking-tight" style={{ fontSize: "clamp(2rem,5vw,3.8rem)", background: "linear-gradient(135deg,var(--txt) 0%,var(--txt-m) 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Turn Chaos<br />into<br /><span style={{ WebkitTextFillColor: "var(--txt)" }}>Clarity.</span>
          </h1>
        </div>
        <p className="text-sm leading-relaxed font-light max-w-md" style={{ color: "var(--txt-m)" }}>
          Upload your CSV and let us handle the architecture. Cleaning, Profiling, and AutoML in one unified pipeline — without writing a <Scratch thickness={1.2}>single line of code.</Scratch>
        </p>
      </div>

      {/* Right Dropzone */}
      <div className="lg:col-span-7">
        <div className={`dz-wrap ${isDragging ? 'dragging' : ''}`} onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }} onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }} onDrop={handleDrop}>
          <div className="gc rounded-[1.3rem] p-6 md:p-8 flex flex-col items-center justify-center text-center relative z-10" style={{ minHeight: "300px" }}>
            {errorMsg && (
              <div className="absolute top-4 left-4 right-4 text-red-400 text-xs font-mono px-4 py-3 rounded-xl" style={{ background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.25)" }}>
                {errorMsg}
              </div>
            )}

            {isUploading && (
              <div className="space-y-3">
                <div className="w-14 h-14 border-2 border-t-transparent rounded-full animate-spin mx-auto" style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }}></div>
                <div>
                  <p className="font-bold text-lg" style={{ color: "var(--txt)" }}>Ingesting dataset…</p>
                  <p className="text-sm mt-1" style={{ color: "var(--txt-m)" }}>{fileName}</p>
                </div>
              </div>
            )}

            {!fileUploaded && !isUploading && (
              <div className="space-y-4 w-full">
                <input type="file" accept=".csv" ref={fileInputRef} className="hidden" onChange={handleFileSelect} />

                {/* Source tabs */}
                <div className="flex gap-1 p-1 rounded-xl w-full" style={{ background: "rgba(255,255,255,.04)", border: "1px solid var(--border)" }}>
                  <button onClick={() => setSourceTab("csv")} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-bold tracking-wide transition-all duration-200 ${sourceTab === 'csv' ? 'text-white shadow' : 'text-[color:var(--txt-m)] hover:text-[color:var(--txt)]'}`} style={sourceTab === 'csv' ? { background: "var(--accent)" } : {}}>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    CSV File
                  </button>
                  <button onClick={() => setSourceTab("sheets")} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-bold tracking-wide transition-all duration-200 ${sourceTab === 'sheets' ? 'text-white shadow' : 'text-[color:var(--txt-m)] hover:text-[color:var(--txt)]'}`} style={sourceTab === 'sheets' ? { background: "var(--accent)" } : {}}>
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zm-7 3h5v2h-5V6zm0 4h5v2h-5v-2zm0 4h5v2h-5v-2zM7 6h3v2H7V6zm0 4h3v2H7v-2zm0 4h3v2H7v-2z" /></svg>
                    Google Sheets
                  </button>
                  <button onClick={() => setSourceTab("database")} className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[11px] font-bold tracking-wide transition-all duration-200 ${sourceTab === 'database' ? 'text-white shadow' : 'text-[color:var(--txt-m)] hover:text-[color:var(--txt)]'}`} style={sourceTab === 'database' ? { background: "var(--accent)" } : {}}>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" /></svg>
                    SQL / Warehouse
                  </button>
                </div>

                {/* CSV Panel */}
                {sourceTab === 'csv' && (
                  <div className="space-y-4">
                    <div className="relative inline-block cursor-pointer" onClick={() => fileInputRef.current?.click()}>
                      <div className="w-20 h-20 border rounded-2xl flex items-center justify-center transform -rotate-6 hover:rotate-0 transition-transform duration-500 mx-auto" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
                        <svg className="w-9 h-9" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 4v16m8-8H4"></path>
                        </svg>
                      </div>
                      <div className="absolute -bottom-2 -right-2 w-10 h-10 border rounded-xl flex items-center justify-center transform rotate-12" style={{ borderColor: "var(--border)", background: "var(--bg)" }}>
                        <svg className="w-4 h-4" style={{ color: "var(--txt)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                        </svg>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xl font-bold tracking-tight" style={{ color: "var(--txt)" }}>Drop the Chaos</h3>
                      <p className="text-sm" style={{ color: "var(--txt-m)" }}>Drag your CSV here or <span className="underline cursor-pointer" style={{ color: "var(--accent)" }} onClick={() => fileInputRef.current?.click()}>browse files</span></p>
                      <p className="text-xs mt-1" style={{ color: "var(--txt-m)", opacity: 0.5 }}>Max 200 MB · CSV only</p>
                    </div>
                    <div className="flex items-center justify-center gap-5 pt-3 border-t" style={{ borderColor: "var(--border)" }}>
                      <div className="flex items-center gap-1.5 opacity-50"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path></svg><span className="text-[10px] font-bold uppercase tracking-widest">Auto-Cleaning</span></div>
                      <div className="flex items-center gap-1.5 opacity-50"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path></svg><span className="text-[10px] font-bold uppercase tracking-widest">AI Profiling</span></div>
                      <div className="flex items-center gap-1.5 opacity-50"><svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path></svg><span className="text-[10px] font-bold uppercase tracking-widest">AutoML</span></div>
                    </div>
                  </div>
                )}

                {/* Sheets Panel */}
                {sourceTab === 'sheets' && (
                  <div className="space-y-4 text-left">
                    <div className="flex items-start gap-3 p-3 rounded-xl" style={{ background: "rgba(46,91,255,.07)", border: "1px solid rgba(46,91,255,.18)" }}>
                      <svg className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                      <p className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>Sheet must be shared as <span style={{ color: "var(--txt)", fontWeight: 600 }}>Anyone with the link can view</span>. In Sheets: <span style={{ color: "var(--txt)" }}>Share → Change to anyone with the link.</span></p>
                    </div>
                    <div className="space-y-2">
                      <label className="block text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Google Sheets URL</label>
                      <div className="relative">
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ color: "var(--txt-m)" }}><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" /></svg></div>
                        <input value={sheetsUrl} onChange={(e) => setSheetsUrl(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') loadSheets(); }} type="text" placeholder="https://docs.google.com/spreadsheets/d/..." className="w-full pl-9 pr-4 py-3 rounded-xl text-xs font-mono outline-none transition-all focus:ring-2" style={{ background: "rgba(255,255,255,.05)", border: "1px solid var(--border)", color: "var(--txt)", borderColor: sheetsError ? "rgba(239,68,68,.5)" : "var(--border)" }} />
                      </div>
                      {sheetsError && <p className="text-[11px] font-medium" style={{ color: "#ef4444" }}>{sheetsError}</p>}
                    </div>
                    <button onClick={loadSheets} disabled={!sheetsUrl.trim() || isSheetsLoading} className="btn-mag w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-all" style={sheetsUrl.trim() && !isSheetsLoading ? { background: "var(--accent)", color: "#fff" } : { background: "rgba(255,255,255,.06)", color: "var(--txt-m)", opacity: 0.55, cursor: "not-allowed" }}>
                      {isSheetsLoading ? (
                        <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                      ) : (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                      )}
                      <span>{isSheetsLoading ? 'Importing...' : 'Import Sheet'}</span>
                    </button>
                  </div>
                )}

                {/* Database / Warehouse Panel */}
                {sourceTab === 'database' && (
                  <div className="space-y-3.5 text-left">
                    {/* Dialect selector pills */}
                    <div>
                      <label className="block text-[10px] font-bold uppercase tracking-widest mb-1.5" style={{ color: "var(--txt-m)" }}>
                        Database / Warehouse Dialect
                      </label>
                      <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
                        {[
                          { id: "postgresql", name: "Postgres", str: "postgresql://postgres:password@localhost:5432/postgres" },
                          { id: "mysql", name: "MySQL", str: "mysql+pymysql://root:password@localhost:3306/mydb" },
                          { id: "snowflake", name: "Snowflake", str: "snowflake://user:password@account/my_db/public?warehouse=compute_wh" },
                          { id: "bigquery", name: "BigQuery", str: "bigquery://gcp-project-id/analytics_dataset" },
                          { id: "clickhouse", name: "ClickHouse", str: "clickhouse+native://default:password@localhost:9000/default" },
                          { id: "sqlite", name: "SQLite", str: "sqlite:///sample.db" },
                        ].map(d => (
                          <button
                            key={d.id}
                            type="button"
                            onClick={() => {
                              setDbDialect(d.id as any);
                              setDbConnStr(d.str);
                              setDbTestResult(null);
                            }}
                            className={`py-1.5 px-2 rounded-lg text-[10px] font-mono font-bold text-center transition-all ${dbDialect === d.id ? 'text-white' : 'hover:bg-white/5'}`}
                            style={{
                              background: dbDialect === d.id ? "var(--accent)" : "rgba(255,255,255,0.03)",
                              border: `1px solid ${dbDialect === d.id ? "var(--accent)" : "var(--border)"}`,
                              color: dbDialect === d.id ? "white" : "var(--txt-m)",
                            }}>
                            {d.name}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Connection String */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <label className="block text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>
                          Connection String (SQLAlchemy URI)
                        </label>
                        <button
                          type="button"
                          onClick={testDbConnection}
                          disabled={!dbConnStr.trim() || isDbTesting}
                          className="text-[10px] font-bold px-2 py-0.5 rounded transition-all flex items-center gap-1"
                          style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1", border: "1px solid rgba(99,102,241,0.25)" }}>
                          {isDbTesting && <svg className="w-2.5 h-2.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>}
                          <span>{isDbTesting ? "Testing..." : "Test Connection"}</span>
                        </button>
                      </div>
                      <input
                        type="text"
                        value={dbConnStr}
                        onChange={(e) => { setDbConnStr(e.target.value); setDbTestResult(null); }}
                        placeholder="postgresql://user:pass@host:5432/dbname"
                        className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none"
                        style={{ background: "rgba(255,255,255,.05)", border: "1px solid var(--border)", color: "var(--txt)" }}
                      />
                      {dbTestResult && (
                        <p className={`text-[10px] font-mono mt-1 ${dbTestResult.ok ? 'text-emerald-400' : 'text-red-400'}`}>
                          {dbTestResult.ok ? "✓ Connection successful! Tables retrieved." : `✗ Connection failed: ${dbTestResult.message}`}
                        </p>
                      )}
                    </div>

                    {/* Ingestion Mode: Table or Query */}
                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>
                            Table or SQL Mode
                          </label>
                          <div className="flex gap-1">
                            <button
                              type="button"
                              onClick={() => setDbQueryMode("table")}
                              className={`text-[9px] px-2 py-0.5 rounded font-bold ${dbQueryMode === 'table' ? 'bg-[var(--accent)] text-white' : 'text-[var(--txt-m)]'}`}>
                              Table
                            </button>
                            <button
                              type="button"
                              onClick={() => setDbQueryMode("sql")}
                              className={`text-[9px] px-2 py-0.5 rounded font-bold ${dbQueryMode === 'sql' ? 'bg-[var(--accent)] text-white' : 'text-[var(--txt-m)]'}`}>
                              Pushdown SQL
                            </button>
                          </div>
                        </div>

                        {dbQueryMode === "table" ? (
                          dbTables.length > 0 ? (
                            <select
                              value={selectedDbTable}
                              onChange={(e) => setSelectedDbTable(e.target.value)}
                              className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none"
                              style={{ background: "rgba(255,255,255,.05)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                              {dbTables.map(t => (
                                <option key={t} value={t}>{t}</option>
                              ))}
                            </select>
                          ) : (
                            <input
                              type="text"
                              value={selectedDbTable}
                              onChange={(e) => setSelectedDbTable(e.target.value)}
                              placeholder="Enter table name (e.g. customers)"
                              className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none"
                              style={{ background: "rgba(255,255,255,.05)", border: "1px solid var(--border)", color: "var(--txt)" }}
                            />
                          )
                        ) : (
                          <textarea
                            rows={2}
                            value={dbCustomSql}
                            onChange={(e) => setDbCustomSql(e.target.value)}
                            placeholder="SELECT * FROM orders WHERE total > 100"
                            className="w-full px-3 py-1.5 rounded-xl text-xs font-mono outline-none"
                            style={{ background: "rgba(255,255,255,.05)", border: "1px solid var(--border)", color: "var(--txt)" }}
                          />
                        )}
                      </div>

                      <div>
                        <label className="text-[10px] font-bold uppercase tracking-widest block mb-1" style={{ color: "var(--txt-m)" }}>
                          Max Ingestion Rows
                        </label>
                        <select
                          value={dbLimit}
                          onChange={(e) => setDbLimit(e.target.value)}
                          className="w-full px-3 py-2 rounded-xl text-xs font-mono outline-none"
                          style={{ background: "rgba(255,255,255,.05)", border: "1px solid var(--border)" , color: "var(--txt)" }}>
                          <option value="1000">1,000 rows (Instant)</option>
                          <option value="5000">5,000 rows (Standard)</option>
                          <option value="25000">25,000 rows (Large)</option>
                          <option value="100000">100,000 rows (Warehouse Dump)</option>
                        </select>
                      </div>
                    </div>

                    {/* Preview Table if generated */}
                    {dbPreview && (
                      <div className="p-2.5 rounded-xl overflow-x-auto max-h-32 text-[10px] font-mono border" style={{ background: "rgba(0,0,0,0.3)", borderColor: "var(--border)" }}>
                        <div className="font-bold text-[9px] uppercase tracking-wider mb-1 text-emerald-400">
                          Preview Sample ({dbPreview.rows?.length} rows):
                        </div>
                        <table className="w-full text-left">
                          <thead>
                            <tr style={{ color: "var(--txt-m)" }}>
                              {dbPreview.columns?.map((c: any) => <th key={c.name} className="pr-3 pb-1">{c.name}</th>)}
                            </tr>
                          </thead>
                          <tbody>
                            {dbPreview.rows?.slice(0, 3).map((r: any, idx: number) => (
                              <tr key={idx} style={{ color: "var(--txt)" }}>
                                {dbPreview.columns?.map((c: any) => <td key={c.name} className="pr-3 truncate max-w-[100px]">{String(r[c.name])}</td>)}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {dbError && <p className="text-[11px] font-mono text-red-400">{dbError}</p>}

                    {/* Action buttons */}
                    <div className="flex gap-2 pt-1">
                      <button
                        type="button"
                        onClick={previewDbData}
                        disabled={isPreviewingDb || !dbConnStr}
                        className="px-3 py-2.5 rounded-xl font-bold text-xs transition-all border"
                        style={{ borderColor: "var(--border)", background: "rgba(255,255,255,0.04)", color: "var(--txt)" }}>
                        {isPreviewingDb ? "Previewing..." : "Preview Sample"}
                      </button>

                      <button
                        type="button"
                        onClick={ingestDbData}
                        disabled={isDbIngesting || !dbConnStr}
                        className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-xs text-white transition-all shadow-md"
                        style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
                        {isDbIngesting && <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>}
                        <span>{isDbIngesting ? "Syncing Database..." : "Ingest into DataForge"}</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Uploaded */}
            {fileUploaded && !isUploading && (
              <div className="w-full space-y-6">
                <div className="flex items-center justify-between w-full p-5 rounded-2xl" style={{ background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.1)" }}>
                  <div className="flex items-center gap-4">
                    <div className="w-11 h-11 rounded-lg flex items-center justify-center text-white font-bold text-xs flex-shrink-0" style={{ background: "var(--accent)" }}>{sourceTab === 'sheets' ? 'GS' : sourceTab === 'database' ? 'SQL' : 'CSV'}</div>
                    <div className="text-left min-w-0">
                      <p className="font-bold truncate max-w-[180px]" style={{ color: "var(--txt)" }}>{fileName}</p>
                      <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>{profile ? `${profile.rows?.toLocaleString()} rows · ${profile.cols} cols` : 'Ready for analysis'}</p>
                    </div>
                  </div>
                  <button onClick={reset} style={{ color: "var(--txt-m)" }} className="hover:opacity-70 transition-opacity flex-shrink-0 ml-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12"></path></svg>
                  </button>
                </div>

                {profile && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <div className="stat-box"><p className="text-[8px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Rows</p><p className="text-lg font-black tracking-tighter mt-0.5" style={{ color: "var(--txt)" }}>{profile.rows?.toLocaleString()}</p></div>
                    <div className="stat-box"><p className="text-[8px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Cols</p><p className="text-lg font-black tracking-tighter mt-0.5" style={{ color: "var(--txt)" }}>{profile.cols}</p></div>
                    <div className="stat-box"><p className="text-[8px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Numeric</p><p className="text-lg font-black tracking-tighter mt-0.5" style={{ color: "var(--txt)" }}>{profile.numeric}</p></div>
                    <div className="stat-box"><p className="text-[8px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Missing</p><p className="text-lg font-black tracking-tighter mt-0.5" style={{ color: "var(--txt)" }}>{profile.missing_pct}%</p></div>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button onClick={() => goToWorkspace(currentUploadId)} className="btn-mag flex items-center justify-center gap-2 py-3.5 rounded-xl font-bold text-white tracking-tight" style={{ background: "var(--accent)" }}>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg> LAUNCH WORKSPACE
                  </button>
                  <button onClick={reset} className="btn-mag border py-3.5 rounded-xl font-bold tracking-tight" style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--txt)" }}>
                    CHANGE FILE
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div >
  );
}
