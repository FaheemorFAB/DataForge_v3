"use client";

import React, { useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import { Download, AlertTriangle, Play, Sparkles } from 'lucide-react';

export function CleanerTab() {
  const { uploadId, setCleanProfile, cleanResult, setCleanResult } = useWorkspace();
  const [isCleaning, setIsCleaning] = useState(false);
  const [cleanError, setCleanError] = useState("");

  const runCleaning = async () => {
    setIsCleaning(true);
    setCleanError("");
    try {
      const res = await apiFetch("/clean", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId }),
      });
      
      if (!res.ok) {
        let errStr = "Server error during cleaning.";
        try {
          const data = await res.json();
          if (data.error) errStr = data.error;
        } catch (e) {}
        setCleanError(errStr);
        setIsCleaning(false);
        return;
      }
      
      const data = await res.json();
      if (data.error) {
        setCleanError(data.error);
        setIsCleaning(false);
        return;
      }
      
      setCleanResult(data);
      setCleanProfile(data.clean_profile);
      
      // Optionally trigger re-fetch of preview data for explorer,
      // handled by ExplorerTab fetching when cleanProfile updates
    } catch (e: any) {
      setCleanError("Network error: " + e.message);
    } finally {
      setIsCleaning(false);
    }
  };

  return (
    <div className="tab-panel space-y-5 px-4 py-4 md:px-6 md:py-6">
      <div className="sec-hd flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
            Data Cleaning
          </h2>
          <p className="sec-sub text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>
            Auto-fix missing values · pyjanitor structural repair · Download cleaned CSV
          </p>
        </div>
        <div className="flex gap-3 flex-wrap">
          {!cleanResult && (
            <button onClick={runCleaning} disabled={isCleaning} className="bp">
              {isCleaning && (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              )}
              <span>{isCleaning ? 'CLEANING DATASET...' : 'CLEAN DATASET'}</span>
            </button>
          )}
          {cleanResult && (
            <>
              <a href={`/api/clean/download?upload_id=${uploadId}`} className="bg flex items-center gap-2" style={{ textDecoration: "none" }}><Download size={14} /> DOWNLOAD CSV</a>
              <a href={`/api/clean/download?format=xlsx&upload_id=${uploadId}`} className="bg flex items-center gap-2" style={{ textDecoration: "none" }}><Download size={14} /> DOWNLOAD EXCEL</a>
            </>
          )}
        </div>
      </div>

      {cleanError && (
        <div className="p-4 rounded-xl space-y-1" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>
          <p className="font-bold text-sm text-red-400 flex items-center gap-1.5"><AlertTriangle size={16} /> Cleaning Failed</p>
          <p className="font-mono text-xs text-red-400">{cleanError}</p>
          <p className="text-[10px] mt-2" style={{ color: "var(--txt-m)" }}>Check that your dataset is uploaded and pyjanitor is installed on the server.</p>
        </div>
      )}

      {isCleaning && !cleanResult && (
        <div className="space-y-6 animate-pulse mt-4">
            <div className="grid-2-4m grid grid-cols-2 md:grid-cols-4 gap-3">
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={`skel-card-${i}`} className="gc p-4 rounded-xl flex flex-col justify-center h-[90px]">
                      <div className="h-2 w-20 rounded mb-3" style={{ background: "var(--border)", opacity: 0.5 }}></div>
                      <div className="h-6 w-24 rounded" style={{ background: "var(--border)", opacity: 0.6 }}></div>
                    </div>
                ))}
            </div>
            
            <div className="mt-6">
                <div className="h-2.5 w-32 rounded mb-4" style={{ background: "var(--border)", opacity: 0.5 }}></div>
                <div className="gc rounded-xl overflow-hidden p-5 space-y-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={`skel-row-${i}`} className="flex gap-4 items-center">
                            <div className="h-3 w-1/4 rounded" style={{ background: "var(--border)", opacity: 0.5 }}></div>
                            <div className="h-3 w-1/4 rounded" style={{ background: "var(--border)", opacity: 0.4 }}></div>
                            <div className="h-3 w-1/4 rounded" style={{ background: "var(--border)", opacity: 0.4 }}></div>
                            <div className="h-3 w-1/4 rounded" style={{ background: "var(--border)", opacity: 0.4 }}></div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
      )}

      {cleanResult && (
        <div className="grid-2-4m grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="gc p-4 rounded-xl">
              <p className="sl">Original Rows</p>
              <p className="text-2xl font-black tracking-tighter mt-1">{cleanResult.stats.original_rows.toLocaleString()}</p>
            </div>
            <div className="gc p-4 rounded-xl">
              <p className="sl">Cleaned Rows</p>
              <p className="text-2xl font-black tracking-tighter mt-1 text-emerald-400">{cleanResult.stats.cleaned_rows.toLocaleString()}</p>
            </div>
            <div className="gc p-4 rounded-xl">
              <p className="sl">Original Cols</p>
              <p className="text-2xl font-black tracking-tighter mt-1">{cleanResult.stats.original_cols}</p>
            </div>
            <div className="gc p-4 rounded-xl">
              <p className="sl">Cleaned Cols</p>
              <p className="text-2xl font-black tracking-tighter mt-1 text-emerald-400">{cleanResult.stats.cleaned_cols}</p>
            </div>
        </div>
      )}

      {cleanResult && cleanResult.missing_log && cleanResult.missing_log.length > 0 && (
        <div>
            <h3 className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--txt-m)" }}>Missing Value Fixes</h3>
            <div className="gc rounded-xl overflow-hidden">
                <div className="tbl-scroll overflow-x-auto">
                    <table className="dt w-full min-w-[480px]">
                        <thead><tr><th>Column</th><th>Missing</th><th>% Missing</th><th>Action</th></tr></thead>
                        <tbody>
                            {cleanResult.missing_log.map((row: any) => (
                                <tr key={row.column} style={{ borderLeft: `3px solid ${row.type === 'drop' ? '#ef4444' : 'var(--accent)'}` }}>
                                    <td className="font-mono" style={{ color: "var(--txt)" }}>{row.column}</td>
                                    <td>{row.missing.toLocaleString()}</td>
                                    <td>{row.pct_missing}%</td>
                                    <td>{row.action}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
      )}

      {cleanResult && (!cleanResult.missing_log || cleanResult.missing_log.length === 0) && (
        <div className="p-4 rounded-xl mt-4 space-y-1" style={{ background: "rgba(16,185,129,.08)", border: "1px solid rgba(16,185,129,.2)" }}>
          <p className="font-bold text-sm text-emerald-400 flex items-center gap-1.5"><Sparkles size={16} /> Dataset Already Clean</p>
          <p className="font-mono text-xs text-emerald-400/80">No missing values or structural anomalies were found. Your dataset is in excellent shape!</p>
        </div>
      )}
    </div>
  );
}
