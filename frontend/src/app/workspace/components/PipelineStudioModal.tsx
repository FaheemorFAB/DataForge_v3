"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  Code,
  Download,
  Copy,
  Check,
  Play,
  X,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";

interface PipelineStudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  uploadId?: string;
}

export function PipelineStudioModal({
  isOpen,
  onClose,
  uploadId,
}: PipelineStudioModalProps) {
  const workspaceContext = useWorkspace();
  const refreshWorkspace = workspaceContext?.refreshWorkspace;

  const [pipelineData, setPipelineData] = useState<any>(null);
  const [qualityResults, setQualityResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [runningAssertions, setRunningAssertions] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState<"code" | "quality">("code");

  const fetchPipelineCode = useCallback(async () => {
    if (!uploadId) return;
    try {
      setLoading(true);
      const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const shareToken = searchParams?.get("share_token") || "";
      const query = shareToken ? `?upload_id=${uploadId}&share_token=${shareToken}` : `?upload_id=${uploadId}`;
      const res = await apiFetch(`/pipeline/export${query}`);
      if (res.ok) {
        const data = await res.json();
        setPipelineData(data);
      }
    } catch (e) {
      console.error("Failed to load pipeline export:", e);
    } finally {
      setLoading(false);
    }
  }, [uploadId]);

  const executeAssertions = useCallback(async () => {
    if (!uploadId) return;
    try {
      setRunningAssertions(true);
      const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const shareToken = searchParams?.get("share_token") || "";
      const res = await apiFetch("/pipeline/assert", {
        method: "POST",
        body: JSON.stringify({ upload_id: uploadId, share_token: shareToken || undefined }),
      });
      if (res.ok) {
        const data = await res.json();
        setQualityResults(data);
      }
    } catch (e) {
      console.error("Failed to run data quality assertions:", e);
    } finally {
      setRunningAssertions(false);
    }
  }, [uploadId]);

  useEffect(() => {
    if (isOpen && uploadId) {
      fetchPipelineCode();
      executeAssertions();
    }
  }, [isOpen, uploadId, fetchPipelineCode, executeAssertions]);

  const copyToClipboard = () => {
    const code = pipelineData?.python_script || "";
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadZip = async () => {
    if (!uploadId) return;
    try {
      const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const shareToken = searchParams?.get("share_token") || "";
      const query = shareToken ? `?upload_id=${uploadId}&share_token=${shareToken}` : `?upload_id=${uploadId}`;
      const res = await apiFetch(`/pipeline/download-zip${query}`);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `dataforge-pipeline-${uploadId.slice(0, 8)}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      const searchParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const shareToken = searchParams?.get("share_token") || "";
      const query = shareToken ? `?upload_id=${uploadId}&share_token=${shareToken}` : `?upload_id=${uploadId}`;
      const link = document.createElement("a");
      link.href = `/api/pipeline/download-zip${query}`;
      link.download = `dataforge-pipeline-${uploadId.slice(0, 8)}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  if (!isOpen) return null;

  const isCleaned = Boolean(pipelineData?.is_cleaned);
  const pythonCode = pipelineData?.python_script || "";
  const integrityScore = qualityResults?.score ?? 100;
  const overallStatus = qualityResults?.overall_status || "PASSED";
  const assertions = qualityResults?.assertions || [];
  const passCount = assertions.filter((a: any) => a.status === "PASSED").length;
  const totalCount = assertions.length;

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div
        className="w-full max-w-3xl max-h-[88vh] rounded-[6px] border shadow-2xl flex flex-col overflow-hidden"
        style={{ background: "var(--bg)", borderColor: "var(--border)", color: "var(--txt)" }}
      >
        {/* HEADER */}
        <div
          className="px-5 py-3.5 border-b flex items-center justify-between shrink-0"
          style={{ background: "var(--nav)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-8 h-8 rounded-[4px] flex items-center justify-center shrink-0"
              style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1", border: "1px solid rgba(99,102,241,0.3)" }}
            >
              <Code size={16} />
            </div>
            <div>
              <h3 className="font-black text-sm" style={{ color: "var(--txt)" }}>Pipeline Studio</h3>
              <p className="text-[10px] font-mono mt-0.5" style={{ color: "var(--txt-m)" }}>
                {isCleaned
                  ? `Cleaned pipeline · ${pipelineData?.cleaning_summary?.rules_count || 1} transform rules applied`
                  : "Raw baseline ingestion · Run Clean & Fix to generate transform rules"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchPipelineCode}
              disabled={loading}
              className="p-1.5 rounded-[4px] border transition-colors cursor-pointer"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
              title="Reload pipeline code"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            </button>
            <button
              onClick={handleDownloadZip}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] text-xs font-bold border transition-colors cursor-pointer"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
              title="Download ZIP"
            >
              <Download size={13} />
              <span>Download ZIP</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-[4px] border transition-colors cursor-pointer"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
            >
              <X size={15} />
            </button>
          </div>
        </div>

        {/* SECTION NAV */}
        <div
          className="px-5 border-b flex items-center justify-between shrink-0"
          style={{ background: "var(--nav)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center">
            {(["code", "quality"] as const).map((sec) => (
              <button
                key={sec}
                onClick={() => setActiveSection(sec)}
                className={`py-2.5 px-3 mr-1 border-b-2 text-xs font-bold transition-colors cursor-pointer flex items-center gap-1.5 ${
                  activeSection === sec
                    ? "border-indigo-500 text-indigo-600 dark:text-indigo-400"
                    : "border-transparent"
                }`}
                style={{ color: activeSection === sec ? undefined : "var(--txt-m)" }}
              >
                {sec === "code" ? (
                  <>
                    <Code size={13} />
                    <span>Python Script</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck size={13} />
                    <span>Quality Gates</span>
                    {totalCount > 0 && (
                      <span
                        className="ml-1 text-[10px] font-black px-1.5 py-0.5 rounded-[3px]"
                        style={{
                          background: passCount === totalCount ? "rgba(16,185,129,0.12)" : "rgba(245,158,11,0.12)",
                          color: passCount === totalCount ? "#10b981" : "#f59e0b",
                          border: `1px solid ${passCount === totalCount ? "rgba(16,185,129,0.25)" : "rgba(245,158,11,0.25)"}`,
                        }}
                      >
                        {passCount}/{totalCount}
                      </span>
                    )}
                  </>
                )}
              </button>
            ))}
          </div>
          {activeSection === "code" && (
            <button
              onClick={copyToClipboard}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] text-xs font-semibold border transition-colors cursor-pointer"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
            >
              {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
          )}
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3">
              <Loader2 size={22} className="animate-spin text-indigo-500" />
              <span className="text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
                Generating Python pipeline…
              </span>
            </div>
          ) : activeSection === "code" ? (
            <div className="p-4">
              {!pythonCode ? (
                <div className="py-16 flex flex-col items-center gap-3 text-center">
                  <Code size={32} style={{ color: "var(--txt-m)" }} />
                  <p className="text-sm font-semibold" style={{ color: "var(--txt-m)" }}>
                    No pipeline code generated yet.
                  </p>
                  <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                    Upload a dataset and run Clean & Fix to auto-generate the Python ETL script.
                  </p>
                </div>
              ) : (
                <div className="relative">
                  <div
                    className="text-[10px] font-mono font-bold uppercase tracking-widest mb-2 flex items-center justify-between"
                    style={{ color: "var(--txt-m)" }}
                  >
                    <span>python etl · auto-generated from workspace state</span>
                    {isCleaned && (
                      <span className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 size={11} />
                        Cleaned Pipeline
                      </span>
                    )}
                  </div>
                  <pre
                    className="p-4 rounded-[4px] text-xs font-mono overflow-x-auto border leading-relaxed"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--txt)",
                      minHeight: "380px",
                      tabSize: 4,
                    }}
                  >
                    {pythonCode}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            /* QUALITY GATES */
            <div className="p-4 space-y-4">
              {/* Score bar */}
              <div
                className="p-4 rounded-[4px] border flex items-center justify-between gap-4 flex-wrap"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                    Data Integrity Score · {isCleaned ? "Post-Cleaning" : "Raw State"}
                  </span>
                  <div className="flex items-baseline gap-2">
                    <span
                      className="text-2xl font-black"
                      style={{ color: overallStatus === "PASSED" ? "#10b981" : "#f59e0b" }}
                    >
                      {integrityScore}%
                    </span>
                    <span
                      className="text-[10px] font-mono font-bold uppercase"
                      style={{ color: overallStatus === "PASSED" ? "#10b981" : "#f59e0b" }}
                    >
                      {overallStatus}
                    </span>
                    {isCleaned && qualityResults?.raw_score !== undefined && (
                      <span className="text-[11px] font-mono" style={{ color: "var(--txt-m)" }}>
                        (was {qualityResults.raw_score}% raw)
                      </span>
                    )}
                    {isCleaned && Number(qualityResults?.improvement_pct || 0) > 0 && (
                      <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                        +{qualityResults.improvement_pct}% gain
                      </span>
                    )}
                  </div>
                  {/* Score track */}
                  <div className="mt-2 w-48 h-1.5 rounded-xs overflow-hidden" style={{ background: "var(--border)" }}>
                    <div
                      className="h-full rounded-xs transition-all duration-700"
                      style={{
                        width: `${integrityScore}%`,
                        background: overallStatus === "PASSED"
                          ? "linear-gradient(90deg,#10b981,#34d399)"
                          : "linear-gradient(90deg,#f59e0b,#fbbf24)",
                      }}
                    />
                  </div>
                </div>

                <button
                  onClick={executeAssertions}
                  disabled={runningAssertions}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-[4px] text-xs font-bold text-white transition-colors cursor-pointer border-0"
                  style={{
                    background: runningAssertions ? "rgba(99,102,241,0.4)" : "linear-gradient(135deg,#6366f1,#8b5cf6)",
                    cursor: runningAssertions ? "not-allowed" : "pointer",
                  }}
                >
                  <Play size={11} fill="currentColor" />
                  {runningAssertions ? "Running…" : "Re-Run Assertions"}
                </button>
              </div>

              {/* Assertions table */}
              {assertions.length > 0 && (
                <div className="rounded-[4px] border overflow-hidden" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                  <div
                    className="px-4 py-2 text-[10px] font-black uppercase tracking-wider border-b"
                    style={{ color: "var(--txt-m)", borderColor: "var(--border)" }}
                  >
                    Assertion Results — {passCount} of {totalCount} passed
                  </div>
                  <div className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {assertions.map((ast: any, i: number) => {
                      const isPass = ast.status === "PASSED";
                      return (
                        <div key={i} className="px-4 py-3 flex items-start justify-between gap-4 text-xs">
                          <div className="flex items-start gap-3">
                            {isPass ? (
                              <CheckCircle2 size={15} className="text-emerald-500 shrink-0 mt-0.5" />
                            ) : (
                              <AlertTriangle size={15} className="text-amber-500 shrink-0 mt-0.5" />
                            )}
                            <div>
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-bold" style={{ color: "var(--txt)" }}>{ast.rule}</span>
                                <span
                                  className="font-mono text-[10px] px-1.5 py-0.5 rounded-[3px] border"
                                  style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                                >
                                  {ast.column}
                                </span>
                                {ast.resolved && (
                                  <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                                    ✓ Resolved by cleaning
                                  </span>
                                )}
                              </div>
                              <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>{ast.message}</p>
                              {ast.resolved && ast.before_val && ast.after_val && (
                                <p className="text-[10px] font-mono mt-0.5 text-emerald-600 dark:text-emerald-400">
                                  Before: {ast.before_val} → After: {ast.after_val}
                                </p>
                              )}
                            </div>
                          </div>
                          <span
                            className="text-[10px] font-bold font-mono uppercase shrink-0 px-2 py-0.5 rounded-[3px]"
                            style={{
                              background: isPass ? "rgba(16,185,129,0.1)" : "rgba(245,158,11,0.1)",
                              color: isPass ? "#10b981" : "#f59e0b",
                              border: `1px solid ${isPass ? "rgba(16,185,129,0.25)" : "rgba(245,158,11,0.25)"}`,
                            }}
                          >
                            {ast.status}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Pytest script */}
              {pipelineData?.data_quality_tests && (
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                    pytest / Great Expectations Script
                  </span>
                  <pre
                    className="p-4 rounded-[4px] text-xs font-mono overflow-x-auto border leading-relaxed"
                    style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                  >
                    {pipelineData.data_quality_tests}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
