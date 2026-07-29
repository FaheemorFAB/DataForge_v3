"use client";

import React, { useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import { Download, AlertTriangle, RefreshCw, Sparkles } from 'lucide-react';

export function EDATab() {
  const { uploadId } = useWorkspace();
  const [isGeneratingEda, setIsGeneratingEda] = useState(false);
  const [edaReady, setEdaReady] = useState(false);
  const [edaError, setEdaError] = useState("");
  const [edaWarning, setEdaWarning] = useState("");
  const [edaMinimal, setEdaMinimal] = useState(false);
  const [edaSampleN, setEdaSampleN] = useState("5000");

  const [bizReportGenerating, setBizReportGenerating] = useState(false);
  const [bizReportReady, setBizReportReady] = useState(false);
  const [bizReportError, setBizReportError] = useState("");

  const runEda = async () => {
    setIsGeneratingEda(true);
    setEdaError("");
    setEdaWarning("");
    try {
      const res = await apiFetch("/eda", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          minimal: edaMinimal,
          sample_n: parseInt(edaSampleN),
          upload_id: uploadId
        }),
      });
      if (!res.ok) {
        let errStr = "EDA failed: unexpected server response. Try enabling Minimal mode.";
        try {
          const text = await res.text();
          try {
            const data = JSON.parse(text);
            if (data.error) errStr = data.error;
          } catch (e) {
            errStr = `EDA failed (HTTP ${res.status}): ${text.substring(0, 150)}`;
          }
        } catch (e) {}
        setEdaError(errStr);
        return;
      }

      const data = await res.json();
      if (data.error) {
        setEdaError(data.error);
        return;
      }

      if (data.warning) setEdaWarning(data.warning);
      if (data.task_id) {
        const pollTask = async (taskId: string) => {
          while (true) {
            await new Promise(r => setTimeout(r, 2000));
            const pRes = await apiFetch(`/tasks/status/${taskId}`);
            if (!pRes.ok) throw new Error("Task check failed");
            const pData = await pRes.json();
            if (pData.status === "success" || pData.status === "completed") return true;
            if (pData.status === "failure" || pData.status === "failed") throw new Error(pData.error || "Task failed");
          }
        };
        await pollTask(data.task_id);
        setEdaReady(true);
      } else if (data.status === "processing") {
        // Handled via websockets originally
      } else {
        setEdaReady(true);
      }
    } catch (e: any) {
      setEdaError("Network error: " + e.message);
    } finally {
      setIsGeneratingEda(false);
    }
  };

  const generateBizReport = async () => {
    setBizReportGenerating(true);
    setBizReportError("");
    try {
      const res = await apiFetch("/data-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId })
      });
      if (!res.ok) {
        let errStr = "Report generation failed.";
        try {
          const data = await res.json();
          if (data.error) errStr = data.error;
        } catch (e) {}
        setBizReportError(errStr);
        return;
      }
      const data = await res.json();
      if (data.error) {
        setBizReportError(data.error);
        return;
      }
      if (data.task_id) {
        const pollTask = async (taskId: string) => {
          while (true) {
            await new Promise(r => setTimeout(r, 2000));
            const pRes = await apiFetch(`/tasks/status/${taskId}`);
            if (!pRes.ok) throw new Error("Task check failed");
            const pData = await pRes.json();
            if (pData.status === "success" || pData.status === "completed") return true;
            if (pData.status === "failure" || pData.status === "failed") throw new Error(pData.error || "Task failed");
          }
        };
        await pollTask(data.task_id);
      }
      setBizReportReady(true);
    } catch (e: any) {
      setBizReportError(String(e));
    } finally {
      setBizReportGenerating(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* ── EDA Report ── */}
      <div className="tab-panel space-y-4 px-4 py-4 md:px-6 md:py-6">
        <div className="sec-hd flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
              EDA Report
            </h2>
            <p className="sec-sub text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>
              ydata-profiling · Distribution · Correlation · Alerts
            </p>
          </div>
          <div className="sec-hd-actions flex items-center gap-2 flex-wrap">
            <label className={`flex items-center gap-2 cursor-pointer ${isGeneratingEda ? 'opacity-50 pointer-events-none' : ''}`}>
              <input type="checkbox" checked={edaMinimal} onChange={e => { setEdaMinimal(e.target.checked); runEda(); }} disabled={isGeneratingEda} style={{ accentColor: "var(--accent)" }} />
              <span className="font-bold uppercase tracking-widest text-[10px]" style={{ color: "var(--txt-m)" }}>Minimal</span>
            </label>
            <select value={edaSampleN} onChange={e => { setEdaSampleN(e.target.value); runEda(); }} disabled={isGeneratingEda} className="inp" style={{ width: "auto", padding: ".4rem .7rem", fontSize: ".75rem", fontWeight: 700 }}>
              <option value="1000">1k rows</option>
              <option value="5000">5k rows</option>
              <option value="0">All rows</option>
            </select>
            <button onClick={runEda} disabled={isGeneratingEda} className="bp">
              {isGeneratingEda && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>}
              <span>{isGeneratingEda ? 'PROFILING...' : (edaReady ? 'UPDATE REPORT' : 'GENERATE REPORT')}</span>
            </button>
            {edaReady && (
              <a href={`/api/eda/report?format=pdf&theme=cupcake&upload_id=${uploadId}`} target="_blank" rel="noopener noreferrer" className="bg flex items-center gap-2" style={{ textDecoration: "none" }}><Download size={14} /> EDA PDF</a>
            )}
          </div>
        </div>

        {edaError && (
          <div className="p-4 rounded-xl space-y-1" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>
            <p className="font-bold text-sm text-red-400 flex items-center gap-1.5"><AlertTriangle size={16} /> EDA Failed</p>
            <p className="font-mono text-xs text-red-400 mt-1">{edaError}</p>
          </div>
        )}

        {edaWarning && (
          <div className="p-4 rounded-xl space-y-1" style={{ background: "rgba(245,158,11,.08)", border: "1px solid rgba(245,158,11,.2)" }}>
            <p className="font-bold text-sm text-yellow-500 flex items-center gap-1.5"><AlertTriangle size={16} /> Report Warning</p>
            <p className="font-mono text-xs text-yellow-500 mt-1">{edaWarning}</p>
          </div>
        )}

        {isGeneratingEda && (
          <div className="gc p-8 rounded-2xl flex flex-col items-center justify-center gap-4 text-center">
            <div className="ld2"></div>
            <div>
              <p className="font-bold text-sm">Generating Profile Report...</p>
              <p className="text-[10px] mt-1" style={{ color: "var(--txt-m)" }}>This may take a minute for large datasets.</p>
            </div>
          </div>
        )}

        {edaReady && !isGeneratingEda && (
          <div className="gc rounded-2xl overflow-hidden p-0" style={{ border: "1px solid var(--border)" }}>
            <iframe id="eda-frame" src={`/api/eda/report?upload_id=${uploadId}`} className="w-full bg-[var(--bg)] border-none block" style={{ borderRadius: ".75rem", height: "clamp(420px, calc(100dvh - 180px), 1000px)" }}></iframe>
          </div>
        )}
      </div>

      {/* ── Business Data Report ── */}
      <div className="tab-panel px-4 pb-4 md:px-6 md:pb-6">
        <div className="flex items-center gap-4 mt-6 mb-4">
            <div className="flex-1 h-px" style={{ background: "var(--border)" }}></div>
            <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Dataforge Business Report</span>
            <div className="flex-1 h-px" style={{ background: "var(--border)" }}></div>
        </div>

        <div className="sec-hd flex items-start justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
              Business Data Report
            </h2>
            <p className="sec-sub text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>
              AI-powered · Full dataset insight · Business analyst narrative · Downloadable
            </p>
          </div>
          <div className="sec-hd-actions flex items-center gap-2 flex-wrap">
            <button onClick={generateBizReport} disabled={bizReportGenerating} className="bp" id="biz-report-generate-btn">
              {bizReportGenerating && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>}
              <span className="flex items-center gap-1.5">{bizReportGenerating ? 'ANALYSING...' : (bizReportReady ? <><RefreshCw size={14}/> UPDATE ANALYSIS</> : <><Sparkles size={14}/> GENERATE ANALYSIS</>)}</span>
            </button>
            {bizReportReady && (
              <a href={`/api/data-report/download?print=true&upload_id=${uploadId}`} target="_blank" rel="noopener noreferrer" className="bg flex items-center gap-2" style={{ textDecoration: "none" }}><Download size={14} /> DOWNLOAD PDF</a>
            )}
          </div>
        </div>

        {bizReportGenerating && (
          <div className="gc p-8 rounded-2xl flex flex-col items-center justify-center gap-4 text-center mt-4">
            <div className="ld2" style={{ background: "var(--accent)", boxShadow: "0 0 6px var(--accent)" }}></div>
            <div>
              <p className="font-bold text-sm">AI Analyst is reviewing your data...</p>
              <p className="text-[10px] mt-1" style={{ color: "var(--txt-m)" }}>Generating business insights and PDF document.</p>
            </div>
          </div>
        )}

        {bizReportReady && !bizReportGenerating && (
          <div className="gc rounded-2xl overflow-hidden mt-4 shadow-xl" style={{ border: "1px solid var(--border)", background: "#E2E8F0", height: "calc(100vh - 220px)", minHeight: 680 }}>
            <iframe src={`/api/reports/latest?upload_id=${uploadId}`} className="w-full h-full border-none block" style={{ background: "#E2E8F0" }}></iframe>
          </div>
        )}

        {bizReportError && (
          <div className="p-4 rounded-xl space-y-1 mt-4" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>
            <p className="font-bold text-sm text-red-400 flex items-center gap-1.5"><AlertTriangle size={16} /> Report Generation Failed</p>
            <p className="font-mono text-xs text-red-400 mt-1">{bizReportError}</p>
          </div>
        )}
      </div>
    </div>
  );
}
