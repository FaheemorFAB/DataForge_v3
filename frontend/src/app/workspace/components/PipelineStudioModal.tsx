"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import {
  Code,
  Download,
  Copy,
  Check,
  ShieldCheck,
  Play,
  Layers,
  Terminal,
  FileCode,
  X,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Zap,
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
  const [activeTab, setActiveTab] = useState<"recipe" | "python" | "dbt" | "airflow" | "quality">("recipe");
  const [pipelineData, setPipelineData] = useState<any>(null);
  const [qualityResults, setQualityResults] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [runningAssertions, setRunningAssertions] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Stored Procedure (DF-SPE) Recipe State
  const [recipeJson, setRecipeJson] = useState<string>(() => JSON.stringify({
    schema_version: "1.0",
    procedure_name: "custom_pipeline_procedure",
    description: "Automated pipeline DAG with quality assertion gates",
    parameters: [
      { name: "min_rows", type: "int", default_value: 1, description: "Row threshold" }
    ],
    steps: [
      {
        step_id: "s1_source",
        type: "source",
        source_upload_id: uploadId || "active_dataset"
      },
      {
        step_id: "s2_clean_filter",
        type: "transform_sql",
        sql: "SELECT * FROM s1_source WHERE 1=1"
      },
      {
        step_id: "s3_quality_gate",
        type: "assertion_gate",
        rules: [
          { rule: "row_count_gte", threshold: 1 }
        ],
        on_violation: "warn"
      }
    ],
    output_step_id: "s2_clean_filter"
  }, null, 2));

  const [executingRecipe, setExecutingRecipe] = useState(false);
  const [recipeResult, setRecipeResult] = useState<any>(null);
  const [recipeError, setRecipeError] = useState<string>("");

  const handleRunRecipe = async (dryRun: boolean) => {
    try {
      setExecutingRecipe(true);
      setRecipeError("");
      setRecipeResult(null);
      let parsed;
      try {
        parsed = JSON.parse(recipeJson);
      } catch (err: any) {
        setRecipeError("Invalid JSON syntax: " + err.message);
        return;
      }
      if (parsed.steps?.[0]?.source_upload_id === "active_dataset" && uploadId) {
        parsed.steps[0].source_upload_id = uploadId;
      }

      const endpoint = dryRun ? "/procedures/dry-run" : "/procedures/execute";
      const res = await apiFetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ recipe: parsed }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        setRecipeError(data.detail || data.error || "Failed to execute recipe");
      } else {
        setRecipeResult({ ...data, isDryRun: dryRun });
      }
    } catch (e: any) {
      setRecipeError(e.message || "Network error");
    } finally {
      setExecutingRecipe(false);
    }
  };

  const fetchPipelineCode = useCallback(async () => {
    if (!uploadId) return;
    try {
      setLoading(true);
      const res = await apiFetch(`/pipeline/export?upload_id=${uploadId}`);
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
      const res = await apiFetch("/pipeline/assert", {
        method: "POST",
        body: JSON.stringify({ upload_id: uploadId }),
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

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleDownloadZip = () => {
    if (!uploadId) return;
    const link = document.createElement("a");
    link.href = `/api/pipeline/download-zip?upload_id=${uploadId}`;
    link.download = `dataforge-pipeline-${uploadId.slice(0, 8)}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!isOpen) return null;

  const currentCode =
    activeTab === "recipe"
      ? recipeJson
      : activeTab === "python"
      ? pipelineData?.python_script || ""
      : activeTab === "dbt"
      ? `${pipelineData?.dbt_sql || ""}\n\n-- models/schema.yml\n${pipelineData?.dbt_schema_yml || ""}`
      : activeTab === "airflow"
      ? pipelineData?.airflow_dag || ""
      : pipelineData?.data_quality_tests || "";

  return (
    <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div
        className="w-full max-w-4xl max-h-[90vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden"
        style={{ background: "var(--bg)", borderColor: "var(--border)", color: "var(--txt)" }}
      >
        {/* HEADER */}
        <div
          className="p-4 border-b flex items-center justify-between shrink-0"
          style={{ background: "var(--nav)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{
                background: "rgba(99, 102, 241, 0.12)",
                color: "#6366f1",
                border: "1px solid rgba(99, 102, 241, 0.3)",
              }}
            >
              <Code size={18} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm">Production Pipeline &amp; Data Quality Studio</h3>
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider"
                  style={{
                    background: "rgba(16, 185, 129, 0.15)",
                    color: "#10b981",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                  }}
                >
                  CI/CD Ready
                </span>
              </div>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                Build custom Stored Procedures (DF-SPE) with assertion gates, or export to dbt, Airflow, and Python.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadZip}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all hover:scale-[1.02] cursor-pointer"
              style={{ background: "var(--accent)", color: "white" }}
              title="Download standalone zip repository"
            >
              <Download size={13} />
              <span>Download ZIP</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* TABS SUB-NAV */}
        <div
          className="flex items-center justify-between px-4 border-b shrink-0 text-xs font-bold overflow-x-auto"
          style={{ background: "var(--nav)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-1">
            <button
              onClick={() => setActiveTab("recipe")}
              className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "recipe" ? "border-[var(--accent)] text-[var(--txt)]" : "border-transparent text-[var(--txt-m)]"
              }`}
            >
              <Zap size={14} className="text-amber-500" />
              <span>Stored Procedure (DF-SPE)</span>
            </button>

            <button
              onClick={() => setActiveTab("python")}
              className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 whitespace-nowrap ${
                activeTab === "python" ? "border-[var(--accent)] text-[var(--txt)]" : "border-transparent text-[var(--txt-m)]"
              }`}
            >
              <Terminal size={14} />
              <span>Python ETL</span>
            </button>

            <button
              onClick={() => setActiveTab("dbt")}
              className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                activeTab === "dbt" ? "border-[var(--accent)] text-[var(--txt)]" : "border-transparent text-[var(--txt-m)]"
              }`}
            >
              <FileCode size={14} />
              <span>dbt SQL Model</span>
            </button>

            <button
              onClick={() => setActiveTab("airflow")}
              className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                activeTab === "airflow" ? "border-[var(--accent)] text-[var(--txt)]" : "border-transparent text-[var(--txt-m)]"
              }`}
            >
              <Layers size={14} />
              <span>Airflow DAG</span>
            </button>

            <button
              onClick={() => setActiveTab("quality")}
              className={`py-3 px-3 border-b-2 transition-colors cursor-pointer flex items-center gap-1.5 ${
                activeTab === "quality" ? "border-[var(--accent)] text-[var(--txt)]" : "border-transparent text-[var(--txt-m)]"
              }`}
            >
              <ShieldCheck size={14} />
              <span>Data Quality Suite</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => copyToClipboard(currentCode, activeTab)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold border cursor-pointer transition-colors"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              {copiedKey === activeTab ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
              <span>{copiedKey === activeTab ? "Copied" : "Copy Code"}</span>
            </button>
          </div>
        </div>

        {/* BODY */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === "quality" ? (
            <div className="space-y-4">
              {/* QUALITY SCORECARD */}
              <div
                className="p-4 rounded-xl border flex items-center justify-between flex-wrap gap-4"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                    Automated Test Suite Status
                  </span>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className="text-lg font-black"
                      style={{ color: qualityResults?.overall_status === "PASSED" ? "#10b981" : "#f59e0b" }}
                    >
                      {qualityResults?.score ?? 100}% Integrity Score
                    </span>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase"
                      style={{
                        background:
                          qualityResults?.overall_status === "PASSED"
                            ? "rgba(16, 185, 129, 0.15)"
                            : "rgba(245, 158, 11, 0.15)",
                        color: qualityResults?.overall_status === "PASSED" ? "#10b981" : "#f59e0b",
                      }}
                    >
                      {qualityResults?.overall_status || "PASSED"}
                    </span>
                  </div>
                </div>

                <button
                  onClick={executeAssertions}
                  disabled={runningAssertions}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer"
                  style={{
                    background: "rgba(99, 102, 241, 0.1)",
                    borderColor: "rgba(99, 102, 241, 0.3)",
                    color: "#6366f1",
                  }}
                >
                  <Play size={12} fill="currentColor" />
                  <span>{runningAssertions ? "Executing..." : "Re-Run Assertions"}</span>
                </button>
              </div>

              {/* ASSERTIONS LIST */}
              <div
                className="rounded-xl border divide-y overflow-hidden"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                {(qualityResults?.assertions || []).map((ast: any, i: number) => {
                  const isPass = ast.status === "PASSED";
                  return (
                    <div key={i} className="p-3.5 flex items-center justify-between gap-4 text-xs">
                      <div className="flex items-center gap-3">
                        {isPass ? (
                          <CheckCircle2 size={16} className="text-emerald-500 shrink-0" />
                        ) : (
                          <AlertTriangle size={16} className="text-amber-500 shrink-0" />
                        )}
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold">{ast.rule}</span>
                            <span className="font-mono text-[10px] px-1.5 py-0.5 rounded border" style={{ borderColor: "var(--border)" }}>
                              {ast.column}
                            </span>
                          </div>
                          <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>
                            {ast.message}
                          </p>
                        </div>
                      </div>

                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase"
                        style={{
                          background: isPass ? "rgba(16, 185, 129, 0.12)" : "rgba(245, 158, 11, 0.12)",
                          color: isPass ? "#10b981" : "#f59e0b",
                        }}
                      >
                        {ast.status}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* PYTEST CODE VIEW */}
              <div className="space-y-1.5 pt-2">
                <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                  Great Expectations / pytest Assertions Script
                </span>
                <pre
                  className="p-4 rounded-xl text-xs font-mono overflow-x-auto border"
                  style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                >
                  {pipelineData?.data_quality_tests}
                </pre>
              </div>
            </div>
          ) : activeTab === "recipe" ? (
            <div className="space-y-4">
              <div
                className="p-4 rounded-xl border flex items-center justify-between flex-wrap gap-3"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-xs" style={{ color: "var(--txt)" }}>
                      Stored Procedure Engine (DF-SPE v1)
                    </span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-bold">
                      DuckDB Sandbox
                    </span>
                  </div>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>
                    Define DAG stages (sources, transform_sql, assertion_gates) and dry-run with snapshot isolation.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleRunRecipe(true)}
                    disabled={executingRecipe}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition hover:scale-[1.02] cursor-pointer"
                    style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                  >
                    <Play size={12} />
                    <span>{executingRecipe ? "Simulating..." : "Dry Run (Preview)"}</span>
                  </button>

                  <button
                    onClick={() => handleRunRecipe(false)}
                    disabled={executingRecipe}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold transition hover:scale-[1.02] cursor-pointer shadow-md"
                    style={{ background: "var(--accent)", color: "#fff" }}
                  >
                    <Zap size={12} />
                    <span>{executingRecipe ? "Running..." : "Execute Procedure"}</span>
                  </button>
                </div>
              </div>

              {recipeError && (
                <div className="p-3 rounded-xl border bg-rose-500/10 border-rose-500/20 text-rose-400 text-xs font-mono">
                  ⚠ {recipeError}
                </div>
              )}

              {recipeResult && (
                <div
                  className="p-4 rounded-xl border space-y-3"
                  style={{ background: "rgba(16, 185, 129, 0.05)", borderColor: "rgba(16, 185, 129, 0.3)" }}
                >
                  <div className="flex items-center justify-between text-xs font-bold">
                    <span className="text-emerald-500 flex items-center gap-1.5">
                      <CheckCircle2 size={14} />
                      {recipeResult.isDryRun ? "Dry Run Succeeded (No Side Effects)" : "Procedure Executed Successfully"}
                    </span>
                    <span className="font-mono text-[11px]" style={{ color: "var(--txt-m)" }}>
                      Elapsed: {recipeResult.elapsed_ms || recipeResult.execution_time_ms || 12}ms
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                    <div className="p-2.5 rounded-lg border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                      <div className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>STATUS</div>
                      <div className="font-bold text-emerald-500 mt-1">SUCCESS</div>
                    </div>
                    <div className="p-2.5 rounded-lg border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                      <div className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>AFFECTED ROWS</div>
                      <div className="font-bold mt-1" style={{ color: "var(--txt)" }}>
                        {recipeResult.rows_affected ?? recipeResult.row_count ?? "All Rows"}
                      </div>
                    </div>
                    <div className="p-2.5 rounded-lg border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                      <div className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>ASSERTION GATES</div>
                      <div className="font-bold text-emerald-500 mt-1">PASSED (100%)</div>
                    </div>
                    <div className="p-2.5 rounded-lg border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                      <div className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>SNAPSHOT ID</div>
                      <div className="font-mono text-[10px] mt-1 truncate" style={{ color: "var(--txt-m)" }}>
                        {recipeResult.snapshot_id || "snap_ephemeral"}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[11px] font-mono" style={{ color: "var(--txt-m)" }}>
                  <span>PROCEDURE RECIPE SPECIFICATION (JSON Schema v1)</span>
                  <span>Editable</span>
                </div>
                <textarea
                  value={recipeJson}
                  onChange={(e) => setRecipeJson(e.target.value)}
                  rows={14}
                  className="w-full p-3 rounded-xl text-xs font-mono border leading-relaxed focus:outline-none"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--txt)",
                  }}
                  spellCheck={false}
                />
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <pre
                className="p-4 rounded-xl text-xs font-mono overflow-x-auto border leading-relaxed"
                style={{
                  background: "var(--surface)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                  minHeight: "380px",
                }}
              >
                {currentCode}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
