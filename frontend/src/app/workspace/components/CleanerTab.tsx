"use client";

import React, { useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import { Download, AlertTriangle, Sparkles, Sliders, Plus, Trash2, CheckCircle2, FileCode } from 'lucide-react';

export function CleanerTab() {
  const { uploadId, profile, setCleanProfile, cleanResult, setCleanResult } = useWorkspace();
  const [mode, setMode] = useState<"auto" | "dynamic">("dynamic");
  const [isCleaning, setIsCleaning] = useState(false);
  const [cleanError, setCleanError] = useState("");

  // Dynamic Rule Builder State
  const [selectedCol, setSelectedCol] = useState("");
  const [actionType, setActionType] = useState<"impute" | "outlier" | "normalize" | "cast" | "drop">("impute");
  const [imputeMethod, setImputeMethod] = useState("median");
  const [fillValue, setFillValue] = useState("");
  const [outlierMethod, setOutlierMethod] = useState("clip");
  const [textCase, setTextCase] = useState("trim");
  const [castType, setCastType] = useState("float");

  const [rules, setRules] = useState<any[]>([]);

  const columns = profile?.columns?.map((c: any) => c.name || c) || [];

  const addRule = () => {
    if (!selectedCol) return;
    const newRule: any = {
      column: selectedCol,
      action_type: actionType,
    };
    if (actionType === "impute") {
      newRule.impute_method = imputeMethod;
      if (imputeMethod === "constant") newRule.fill_value = fillValue;
    } else if (actionType === "outlier") {
      newRule.outlier_method = outlierMethod;
    } else if (actionType === "normalize") {
      newRule.text_case = textCase;
    } else if (actionType === "cast") {
      newRule.cast_type = castType;
    }
    setRules(prev => [...prev.filter(r => r.column !== selectedCol || r.action_type !== actionType), newRule]);
  };

  const removeRule = (idx: number) => {
    setRules(prev => prev.filter((_, i) => i !== idx));
  };

  // Run 1-Click Auto Clean
  const runAutoCleaning = async () => {
    setIsCleaning(true);
    setCleanError("");
    try {
      const res = await apiFetch("/clean", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setCleanError(data.error || "Cleaning failed");
        return;
      }
      setCleanResult(data);
      setCleanProfile(data.clean_profile);
    } catch (e: any) {
      setCleanError("Network error: " + e.message);
    } finally {
      setIsCleaning(false);
    }
  };

  // Run Dynamic Custom Rules Clean
  const runDynamicCleaning = async () => {
    if (rules.length === 0) return;
    setIsCleaning(true);
    setCleanError("");
    try {
      const res = await apiFetch("/clean/dynamic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, rules }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setCleanError(data.error || "Dynamic cleaning failed");
        return;
      }
      setCleanResult(data);
      setCleanProfile(data.clean_profile);
    } catch (e: any) {
      setCleanError("Network error: " + e.message);
    } finally {
      setIsCleaning(false);
    }
  };

  return (
    <div className="tab-panel space-y-6 px-4 py-4 md:px-6 md:py-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
            Data Cleaning Studio
          </h2>
          <p className="text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>
            Interactive per-column rules · Real-time imputation · Outlier clipping · Type casting · CSV/Excel export
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Mode Switcher */}
          <div className="flex p-1 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <button onClick={() => setMode("dynamic")} className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
              style={mode === "dynamic" ? { background: "#6366f1", color: "#fff", boxShadow: "0 0 12px rgba(99,102,241,0.3)" } : { color: "var(--txt-m)" }}>
              <Sliders size={13} /> Dynamic Studio
            </button>
            <button onClick={() => setMode("auto")} className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
              style={mode === "auto" ? { background: "#6366f1", color: "#fff", boxShadow: "0 0 12px rgba(99,102,241,0.3)" } : { color: "var(--txt-m)" }}>
              <Sparkles size={13} /> 1-Click Auto
            </button>
          </div>

          {cleanResult && (
            <div className="flex gap-2">
              <a href={`/api/clean/download?upload_id=${uploadId}`} className="bg flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border" style={{ textDecoration: "none" }}><Download size={13} /> CSV</a>
              <a href={`/api/clean/download?format=xlsx&upload_id=${uploadId}`} className="bg flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border" style={{ textDecoration: "none" }}><Download size={13} /> EXCEL</a>
            </div>
          )}
        </div>
      </div>

      {cleanError && (
        <div className="p-4 rounded-xl space-y-1" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>
          <p className="font-bold text-sm text-red-400 flex items-center gap-1.5"><AlertTriangle size={16} /> Cleaning Error</p>
          <p className="font-mono text-xs text-red-400">{cleanError}</p>
        </div>
      )}

      {/* ── MODE 1: 1-Click Automated Cleaner ────────────────────────── */}
      {mode === "auto" && (
        <div className="rounded-2xl p-6 space-y-4" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.07)" }}>
          <div>
            <p className="font-black text-base" style={{ color: "var(--txt)" }}>Automated 1-Click Cleaning</p>
            <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
              Automatically normalizes column names to snake_case, drops &gt;60% missing columns, imputes remaining missing values using skewness heuristics (Mean/Median/Mode), and strips extra whitespace.
            </p>
          </div>
          <button onClick={runAutoCleaning} disabled={isCleaning} className="px-6 py-3 rounded-xl font-bold text-sm text-white flex items-center gap-2"
            style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>
            {isCleaning ? <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg> : <Sparkles size={16} />}
            {isCleaning ? "Cleaning Dataset…" : "Run Automated Clean"}
          </button>
        </div>
      )}

      {/* ── MODE 2: Dynamic Custom Rule Studio ───────────────────────── */}
      {mode === "dynamic" && (
        <div className="space-y-6">
          {/* Rule Builder Form */}
          <div className="rounded-2xl overflow-hidden" style={{ background: "var(--surface)", border: "1px solid rgba(99,102,241,0.2)", boxShadow: "0 4px 30px rgba(99,102,241,0.05)" }}>
            <div className="flex items-center gap-3 px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", background: "rgba(99,102,241,0.05)" }}>
              <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}><Sliders size={14} className="text-white" /></div>
              <div><p className="text-sm font-black uppercase tracking-wide" style={{ color: "var(--txt)" }}>Custom Rule Builder</p><p className="text-[10px]" style={{ color: "var(--txt-m)" }}>Configure granular cleaning actions per column</p></div>
            </div>

            <div className="p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                {/* 1. Target Column */}
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Select Column</label>
                  <select value={selectedCol} onChange={e => setSelectedCol(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem 0.75rem" }}>
                    <option value="">— Choose Column —</option>
                    {columns.map((c: string) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>

                {/* 2. Action Category */}
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Action Category</label>
                  <select value={actionType} onChange={e => setActionType(e.target.value as any)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem 0.75rem" }}>
                    <option value="impute">Impute Missing Values</option>
                    <option value="outlier">Handle Outliers</option>
                    <option value="normalize">Normalize Text</option>
                    <option value="cast">Type Casting</option>
                    <option value="drop">Drop Column</option>
                  </select>
                </div>

                {/* 3. Method Selection */}
                {actionType === "impute" && (
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Imputation Strategy</label>
                    <select value={imputeMethod} onChange={e => setImputeMethod(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem 0.75rem" }}>
                      <option value="median">Fill with Median</option>
                      <option value="mean">Fill with Mean</option>
                      <option value="mode">Fill with Mode (Most Frequent)</option>
                      <option value="zero">Fill with Zero (0)</option>
                      <option value="constant">Fill with Custom Constant</option>
                      <option value="ffill">Forward Fill (ffill)</option>
                      <option value="bfill">Backward Fill (bfill)</option>
                      <option value="drop_rows">Drop Rows with Missing</option>
                    </select>
                  </div>
                )}

                {actionType === "impute" && imputeMethod === "constant" && (
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Custom Fill Value</label>
                    <input type="text" value={fillValue} onChange={e => setFillValue(e.target.value)} placeholder="e.g. N/A or 0" className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem 0.75rem" }} />
                  </div>
                )}

                {actionType === "outlier" && (
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Outlier Strategy</label>
                    <select value={outlierMethod} onChange={e => setOutlierMethod(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem 0.75rem" }}>
                      <option value="clip">Clip Outliers (1st/99th Percentile)</option>
                      <option value="fill_median">Replace Outliers with Median</option>
                      <option value="drop_rows">Remove Outlier Rows</option>
                    </select>
                  </div>
                )}

                {actionType === "normalize" && (
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Text Transformation</label>
                    <select value={textCase} onChange={e => setTextCase(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem 0.75rem" }}>
                      <option value="trim">Trim Whitespace</option>
                      <option value="lowercase">Convert to Lowercase</option>
                      <option value="uppercase">Convert to Uppercase</option>
                    </select>
                  </div>
                )}

                {actionType === "cast" && (
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Target Data Type</label>
                    <select value={castType} onChange={e => setCastType(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem 0.75rem" }}>
                      <option value="float">Numeric (Float)</option>
                      <option value="int">Integer</option>
                      <option value="datetime">Datetime</option>
                      <option value="string">Text (String)</option>
                    </select>
                  </div>
                )}

                <div className="flex items-end">
                  <button onClick={addRule} disabled={!selectedCol}
                    className="w-full px-4 py-2 rounded-xl text-xs font-bold text-white flex items-center justify-center gap-1.5 transition-all"
                    style={!selectedCol ? { background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.3)", cursor: "not-allowed" } : { background: "#6366f1", boxShadow: "0 0 14px rgba(99,102,241,0.3)" }}>
                    <Plus size={14} /> Add Rule
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Active Rules Queue */}
          {rules.length > 0 && (
            <div className="rounded-2xl p-5 space-y-4" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.07)" }}>
              <div className="flex items-center justify-between">
                <p className="text-xs font-black uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Configured Rules Stack ({rules.length})</p>
                <button onClick={() => setRules([])} className="text-[10px] font-bold text-red-400 hover:underline flex items-center gap-1"><Trash2 size={12} /> Clear All</button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {rules.map((r, i) => (
                  <div key={i} className="rounded-xl p-3 flex items-center justify-between gap-2" style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}>
                    <div>
                      <p className="text-xs font-bold font-mono text-indigo-400">{r.column}</p>
                      <p className="text-[10px] uppercase font-bold mt-0.5" style={{ color: "var(--txt-m)" }}>
                        {r.action_type === "impute" && `Impute: ${r.impute_method}`}
                        {r.action_type === "outlier" && `Outliers: ${r.outlier_method}`}
                        {r.action_type === "normalize" && `Text: ${r.text_case}`}
                        {r.action_type === "cast" && `Cast: ${r.cast_type}`}
                        {r.action_type === "drop" && "Action: Drop Column"}
                      </p>
                    </div>
                    <button onClick={() => removeRule(i)} className="w-6 h-6 rounded flex items-center justify-center text-gray-500 hover:text-red-400 transition-all"><Trash2 size={12} /></button>
                  </div>
                ))}
              </div>

              <button onClick={runDynamicCleaning} disabled={isCleaning} className="w-full py-3 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2"
                style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>
                {isCleaning ? <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg> : <CheckCircle2 size={16} />}
                {isCleaning ? "Applying Dynamic Pipeline…" : "Apply Dynamic Pipeline"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Results Cards & Audit Log ──────────────────────────────────── */}
      {cleanResult && (
        <div className="space-y-6 mt-6">
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

          {cleanResult.missing_log && cleanResult.missing_log.length > 0 && (
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--txt-m)" }}>Cleaning Action Audit Log</h3>
              <div className="gc rounded-xl overflow-hidden">
                <div className="tbl-scroll overflow-x-auto">
                  <table className="dt w-full min-w-[480px]">
                    <thead><tr><th>Target Column</th><th>Type</th><th>Action Performed</th></tr></thead>
                    <tbody>
                      {cleanResult.missing_log.map((row: any, i: number) => (
                        <tr key={i} style={{ borderLeft: `3px solid ${row.type === 'drop' ? '#ef4444' : row.type === 'outlier' ? '#f59e0b' : '#10b981'}` }}>
                          <td className="font-mono font-bold" style={{ color: "var(--txt)" }}>{row.column}</td>
                          <td><span className="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.05)", color: "var(--txt-m)" }}>{row.type || "clean"}</span></td>
                          <td style={{ color: "var(--txt)" }}>{row.action}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
