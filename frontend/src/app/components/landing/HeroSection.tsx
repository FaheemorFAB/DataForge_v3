"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

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

  const [sourceTab, setSourceTab] = useState<"csv" | "sheets">("csv");
  const [sheetsUrl, setSheetsUrl] = useState("");
  const [sheetsError, setSheetsError] = useState("");
  const [isSheetsLoading, setIsSheetsLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (isLoggedIn && !fileUploaded) {
      // Check if we have an upload in localStorage first to avoid flash
      const lastUpload = localStorage.getItem('df_last_upload');
      
      apiFetch('/projects')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data) && data.length > 0) {
            const latest = data[0];
            setFileName(latest.filename || 'Existing Dataset');
            setCurrentUploadId(latest.id);
            localStorage.setItem('df_last_upload', latest.id);
            
            // Reconstruct a mock profile for the UI from the project list stats
            setProfile({
              rows: latest.rows,
              cols: latest.cols,
              numeric: latest.numeric || 0,
              missing_pct: latest.missing_pct || 0
            });
            
            setFileUploaded(true);
          } else {
             localStorage.removeItem('df_last_upload');
          }
        })
        .catch(err => console.error("Failed to fetch projects:", err));
    }
  }, [isLoggedIn, fileUploaded]);

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
      localStorage.setItem('df_last_upload', data.upload_id);
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

  const reset = () => {
    setFileUploaded(false); setFileName(''); setProfile(null);
    setErrorMsg(''); setSheetsUrl(''); setSheetsError('');
    setCurrentUploadId(null);
    localStorage.removeItem('df_last_upload');
  };

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
      localStorage.setItem('df_last_upload', data.upload_id);
      setFileUploaded(true);
      goToWorkspace(data.upload_id);
    } catch (err: any) {
      setSheetsError('Network error: ' + err.message);
    } finally {
      setIsSheetsLoading(false);
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
          Upload your CSV and let us handle the architecture. Cleaning, Profiling, and AutoML in one unified pipeline.
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
                  <button onClick={() => setSourceTab("csv")} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-[11px] font-bold tracking-wide transition-all duration-200 ${sourceTab === 'csv' ? 'text-white shadow' : 'text-[color:var(--txt-m)] hover:text-[color:var(--txt)]'}`} style={sourceTab === 'csv' ? { background: "var(--accent)" } : {}}>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                    CSV File
                  </button>
                  <button onClick={() => setSourceTab("sheets")} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-[11px] font-bold tracking-wide transition-all duration-200 ${sourceTab === 'sheets' ? 'text-white shadow' : 'text-[color:var(--txt-m)] hover:text-[color:var(--txt)]'}`} style={sourceTab === 'sheets' ? { background: "var(--accent)" } : {}}>
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V5a2 2 0 00-2-2zm-7 3h5v2h-5V6zm0 4h5v2h-5v-2zm0 4h5v2h-5v-2zM7 6h3v2H7V6zm0 4h3v2H7v-2zm0 4h3v2H7v-2z" /></svg>
                    Google Sheets
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
              </div>
            )}

            {/* Uploaded */}
            {fileUploaded && !isUploading && (
              <div className="w-full space-y-6">
                <div className="flex items-center justify-between w-full p-5 rounded-2xl" style={{ background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.1)" }}>
                  <div className="flex items-center gap-4">
                    <div className="w-11 h-11 rounded-lg flex items-center justify-center text-white font-bold text-xs flex-shrink-0" style={{ background: "var(--accent)" }}>{sourceTab === 'sheets' ? 'GS' : 'CSV'}</div>
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
                  <div className="grid grid-cols-4 gap-2">
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

        {isLoggedIn && (
          <a href="/workspace" className="mt-4 flex items-center justify-between w-full px-4 py-3 rounded-xl border transition-all group" style={{ borderColor: "var(--border)", background: "var(--surface)", textDecoration: "none" }}>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(46,91,255,.1)" }}>
                <svg className="w-4 h-4" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>
              </div>
              <div>
                <p className="text-xs font-bold" style={{ color: "var(--txt)" }}>Go to Workspace</p>
                <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>Resume a past analysis with full context</p>
              </div>
            </div>
            <svg className="w-4 h-4 transition-transform group-hover:translate-x-0.5" style={{ color: "var(--txt-m)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
          </a>
        )}
      </div>
    </div>
  );
}
