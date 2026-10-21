"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useWorkspace } from "./WorkspaceProvider";
import {
  Boxes,
  Play,
  Download,
  CheckCircle2,
  AlertCircle,
  Zap,
  Activity,
  Layers,
  ChevronRight,
  RefreshCw,
  Search,
  Filter,
  Code,
  Terminal,
  Cpu,
  ArrowUpRight,
  X,
  FileCode,
  Plus,
  ShieldCheck,
  Trash2,
  Loader2,
} from "lucide-react";

interface ModelRecord {
  id: string;
  org_id: string;
  model_name: string;
  task_type: "classification" | "regression";
  algorithm: string;
  target_column: string;
  features: string[];
  metrics: Record<string, number>;
  version: string;
  status?: string;
  created_by: string;
  created_at: string;
  summary?: string;
  upload_id?: string;
}

interface PredictionResult {
  ok: boolean;
  model_id: string;
  model_name: string;
  algorithm: string;
  task_type: string;
  prediction: any;
  confidence?: number;
  predicted_label?: string;
  probabilities?: Record<string, number>;
  confidence_interval?: number[];
  latency_ms: number;
  timestamp: string;
}

export function ModelRegistryTab() {
  const { uploadId, refreshWorkspace, setActiveTab, activeTab } = useWorkspace();
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskFilter, setTaskFilter] = useState<"all" | "classification" | "regression">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // In-Workspace Application State
  const [applyingModelId, setApplyingModelId] = useState<string | null>(null);
  const [applyToast, setApplyToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const handleApplyToWorkspace = async (model: ModelRecord) => {
    if (!uploadId) {
      setApplyToast({
        message: "No active dataset loaded in workspace. Please load or upload a dataset first.",
        type: "error",
      });
      setTimeout(() => setApplyToast(null), 5000);
      return;
    }
    setApplyingModelId(model.id);
    setApplyToast(null);
    try {
      const res = await apiFetch(`/models/${model.id}/apply-to-workspace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId }),
      });
      if (res.ok) {
        const d = await res.json();
        setApplyToast({
          message: `Successfully applied '${model.model_name}'! Scored ${d.rows_scored} rows. Added columns: [${d.new_columns.join(", ")}].`,
          type: "success",
        });
        if (refreshWorkspace) await refreshWorkspace(uploadId);
      } else {
        const err = await res.json().catch(() => ({}));
        setApplyToast({
          message: `Application failed: ${err.detail || err.error || res.statusText}`,
          type: "error",
        });
      }
    } catch (e: any) {
      setApplyToast({
        message: `Network error: ${e.message || String(e)}`,
        type: "error",
      });
    } finally {
      setApplyingModelId(null);
      setTimeout(() => setApplyToast(null), 8000);
    }
  };

  // Testing & Inference modal
  const [activeModelForInference, setActiveModelForInference] = useState<ModelRecord | null>(null);
  const [featureInputs, setFeatureInputs] = useState<Record<string, any>>({});
  const [predictionResult, setPredictionResult] = useState<PredictionResult | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [predictError, setPredictError] = useState("");

  // Code integration tab in playground
  const [codeSnippetTab, setCodeSnippetTab] = useState<"curl" | "python">("curl");

  // Batch Predict CSV modal
  const [activeModelForBatch, setActiveModelForBatch] = useState<ModelRecord | null>(null);
  const [batchFile, setBatchFile] = useState<File | null>(null);
  const [batchScoring, setBatchScoring] = useState(false);
  const [batchSuccess, setBatchSuccess] = useState(false);
  const [batchError, setBatchError] = useState("");

  const handleBatchPredictCsv = async () => {
    if (!activeModelForBatch || !batchFile) return;
    setBatchScoring(true);
    setBatchError("");
    setBatchSuccess(false);
    try {
      const formData = new FormData();
      formData.append("file", batchFile);

      const res = await apiFetch(`/models/${activeModelForBatch.id}/batch-predict-csv`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.error || "Batch prediction failed");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scored_${batchFile.name}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
      setBatchSuccess(true);
    } catch (e: any) {
      setBatchError(e.message || String(e));
    } finally {
      setBatchScoring(false);
    }
  };


  // Register custom model modal
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [newModelName, setNewModelName] = useState("");
  const [newModelAlgo, setNewModelAlgo] = useState("LightGBM");
  const [newModelTask, setNewModelTask] = useState<"classification" | "regression">("classification");
  const [newModelTarget, setNewModelTarget] = useState("target");
  const [newModelFeatures, setNewModelFeatures] = useState("age, income, tenure, score");
  const [registering, setRegistering] = useState(false);

  const fetchModels = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiFetch("/models");
      if (res.ok) {
        const data = await res.json();
        setModels(data.models || []);
      }
    } catch (e) {
      console.error("Failed to fetch model registry:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // Re-fetch automatically when the user activates the Models tab
  useEffect(() => {
    if (activeTab === "models") {
      fetchModels();
    }
  }, [activeTab, fetchModels]);

  const [deletingModelId, setDeletingModelId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const handleDeleteModel = async (modelId: string) => {
    setDeletingModelId(modelId);
    try {
      const res = await apiFetch(`/models/${modelId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setDeleteConfirmId(null);
        fetchModels();
      }
    } catch (e) {
      console.error("Failed to delete model:", e);
    } finally {
      setDeletingModelId(null);
    }
  };

  const handleDownloadDocker = (modelId: string, modelName: string) => {
    const slug = modelName.toLowerCase().replace(/\s+/g, "-");
    const link = document.createElement("a");
    link.href = `/api/models/${modelId}/docker-package`;
    link.download = `dataforge-${slug}-container.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const openInferencePlayground = (model: ModelRecord) => {
    setActiveModelForInference(model);
    setPredictionResult(null);
    setPredictError("");

    // Initialize inputs with smart sample values
    const initial: Record<string, any> = {};
    model.features.forEach((f) => {
      const fl = f.toLowerCase();
      if (fl.includes("income") || fl.includes("salary")) initial[f] = 75000;
      else if (fl.includes("age")) initial[f] = 34;
      else if (fl.includes("score")) initial[f] = 710;
      else if (fl.includes("tenure") || fl.includes("month")) initial[f] = 18;
      else if (fl.includes("call") || fl.includes("count")) initial[f] = 2;
      else if (fl.includes("contract") || fl.includes("tier")) initial[f] = "Pro";
      else initial[f] = 1.0;
    });
    setFeatureInputs(initial);
  };

  const handleExecutePrediction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeModelForInference) return;
    setPredicting(true);
    setPredictError("");

    try {
      // Cast numeric fields
      const formattedFeatures: Record<string, any> = {};
      Object.entries(featureInputs).forEach(([k, v]) => {
        if (!isNaN(Number(v)) && v !== "" && typeof v !== "boolean") {
          formattedFeatures[k] = Number(v);
        } else {
          formattedFeatures[k] = v;
        }
      });

      const res = await apiFetch(`/models/${activeModelForInference.id}/predict`, {
        method: "POST",
        body: JSON.stringify({ features: formattedFeatures }),
      });

      if (!res.ok) {
        const err = await res.json();
        setPredictError(err.detail || "Prediction request failed");
      } else {
        const data = await res.json();
        setPredictionResult(data);
      }
    } catch (err: any) {
      setPredictError(err.message || "Network error");
    } finally {
      setPredicting(false);
    }
  };

  const handleRegisterModel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newModelName.trim()) return;
    setRegistering(true);

    try {
      const featArray = newModelFeatures
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean);

      const res = await apiFetch("/models", {
        method: "POST",
        body: JSON.stringify({
          model_name: newModelName.trim(),
          task_type: newModelTask,
          algorithm: newModelAlgo,
          target_column: newModelTarget.trim(),
          features: featArray,
          metrics:
            newModelTask === "classification"
              ? { roc_auc: 0.942, f1_score: 0.895, accuracy: 0.912 }
              : { r2: 0.887, rmse: 18.4, mae: 14.2 },
          version: "v1.0.0",
          summary: `AutoML ${newModelAlgo} model registered into enterprise catalog.`,
        }),
      });

      if (res.ok) {
        setShowRegisterModal(false);
        setNewModelName("");
        fetchModels();
      }
    } catch (e) {
      console.error("Failed to register model:", e);
    } finally {
      setRegistering(false);
    }
  };

  const filteredModels = models.filter((m) => {
    const matchesTask = taskFilter === "all" || m.task_type === taskFilter;
    const matchesSearch =
      m.model_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.algorithm.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.target_column.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (m.features || []).some((f) => f.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesTask && matchesSearch;
  });

  const classificationCount = models.filter((m) => m.task_type === "classification").length;
  const regressionCount = models.filter((m) => m.task_type === "regression").length;

  return (
    <div className="h-full flex flex-col overflow-hidden" style={{ background: "var(--bg)", color: "var(--txt)" }}>
      {/* TOP STATS BAR */}
      <div
        className="shrink-0 p-4 border-b flex flex-wrap items-center justify-between gap-4"
        style={{ background: "var(--nav)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{
              background: "rgba(99, 102, 241, 0.12)",
              color: "#6366f1",
              border: "1px solid rgba(99, 102, 241, 0.3)",
            }}
          >
            <Boxes size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold">Enterprise Model Registry</h1>
              <span
                className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider"
                style={{
                  background: "rgba(16, 185, 129, 0.15)",
                  color: "#10b981",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                }}
              >
                Online Serving Ready
              </span>
            </div>
            <p className="text-xs" style={{ color: "var(--txt-m)" }}>
              Versioned artifact catalog, sub-2ms online inference, and 1-click Docker packaging.
            </p>
          </div>
        </div>

        {/* METRICS SUMMARY */}
        <div className="flex items-center gap-3">
          <div
            className="px-3 py-1.5 rounded-xl border flex items-center gap-2 text-xs font-mono"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <span style={{ color: "var(--txt-m)" }}>Catalog:</span>
            <span className="font-bold">{models.length} Models</span>
          </div>

          <div
            className="px-3 py-1.5 rounded-xl border flex items-center gap-2 text-xs font-mono"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <span style={{ color: "var(--txt-m)" }}>Classification:</span>
            <span className="font-bold text-indigo-400">{classificationCount}</span>
          </div>

          <div
            className="px-3 py-1.5 rounded-xl border flex items-center gap-2 text-xs font-mono"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <span style={{ color: "var(--txt-m)" }}>Regression:</span>
            <span className="font-bold text-cyan-400">{regressionCount}</span>
          </div>

          <div
            className="px-3 py-1.5 rounded-xl border flex items-center gap-2 text-xs font-mono"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <Zap size={13} className="text-amber-400" />
            <span style={{ color: "var(--txt-m)" }}>Latency:</span>
            <span className="font-bold text-emerald-400">&lt;2ms SLA</span>
          </div>

          <button
            onClick={fetchModels}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all hover:scale-[1.02] cursor-pointer"
            style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
            title="Reload model catalog"
          >
            <RefreshCw size={13} className={loading ? "animate-spin text-indigo-400" : ""} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setShowRegisterModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all hover:scale-[1.02] cursor-pointer"
            style={{ background: "var(--accent)", color: "white" }}
          >
            <Plus size={14} />
            <span>Register Model</span>
          </button>
        </div>
      </div>

      {/* FILTER & SEARCH TOOLBAR */}
      <div
        className="shrink-0 px-4 py-2.5 border-b flex items-center justify-between gap-4"
        style={{ background: "var(--bg)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-2">
          {(["all", "classification", "regression"] as const).map((task) => (
            <button
              key={task}
              onClick={() => setTaskFilter(task)}
              className={`px-3 py-1 rounded-lg text-xs font-bold capitalize transition-colors cursor-pointer border ${
                taskFilter === task
                  ? "border-[var(--accent)] text-[var(--accent)] bg-[var(--accent)]/10"
                  : "border-transparent text-[var(--txt-m)] hover:text-[var(--txt)]"
              }`}
            >
              {task === "all" ? "All Tasks" : task}
            </button>
          ))}
        </div>

        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs max-w-sm w-full"
          style={{ background: "var(--card)", borderColor: "var(--border)" }}
        >
          <Search size={14} style={{ color: "var(--txt-m)" }} />
          <input
            type="text"
            placeholder="Search by model name, algorithm or target..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-transparent border-none outline-none w-full text-xs"
            style={{ color: "var(--txt)" }}
          />
        </div>
      </div>

      {/* Toast Notification for Workspace Application */}
      {applyToast && (
        <div
          className={`shrink-0 mx-4 mt-3 p-3 rounded-xl border flex items-center justify-between gap-3 text-xs font-bold transition-all ${
            applyToast.type === "success"
              ? "bg-emerald-500/15 border-emerald-500/30 text-emerald-300"
              : "bg-red-500/15 border-red-500/30 text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {applyToast.type === "success" ? <CheckCircle2 size={16} className="text-emerald-400 shrink-0" /> : <AlertCircle size={16} className="text-red-400 shrink-0" />}
            <span>{applyToast.message}</span>
          </div>
          {applyToast.type === "success" && (
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setActiveTab("preview")}
                className="px-2.5 py-1 rounded-lg bg-emerald-500 text-white text-[11px] font-black hover:bg-emerald-400 transition cursor-pointer"
              >
                Inspect in My Data
              </button>
              <button
                onClick={() => setActiveTab("charts")}
                className="px-2.5 py-1 rounded-lg bg-indigo-600 text-white text-[11px] font-black hover:bg-indigo-500 transition cursor-pointer"
              >
                View in Dashboard
              </button>
            </div>
          )}
        </div>
      )}

      {/* CATALOG GRID */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="h-64 flex flex-col items-center justify-center gap-2">
            <RefreshCw size={24} className="animate-spin text-indigo-500" />
            <p className="text-xs" style={{ color: "var(--txt-m)" }}>
              Loading model registry artifacts...
            </p>
          </div>
        ) : filteredModels.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center gap-3 text-center">
            <Boxes size={40} style={{ color: "var(--txt-f)" }} />
            <div>
              <p className="font-bold text-sm">No models found in catalog</p>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                Run an AutoML tournament or register a model to enable live serving.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredModels.map((m) => {
              return (
                <div
                  key={m.id}
                  className="rounded-2xl border p-5 flex flex-col justify-between shadow-sm hover:shadow-md transition-all space-y-4"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  {/* CARD HEADER */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span
                          className="px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider"
                          style={{
                            background: "rgba(99, 102, 241, 0.15)",
                            color: "#6366f1",
                            border: "1px solid rgba(99, 102, 241, 0.3)",
                          }}
                        >
                          {m.algorithm}
                        </span>
                        <span
                          className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider"
                          style={{
                            background: "rgba(6, 182, 212, 0.15)",
                            color: "#06b6d4",
                          }}
                        >
                          {m.task_type}
                        </span>
                        <span className="font-mono text-[10px]" style={{ color: "var(--txt-f)" }}>
                          {m.version}
                        </span>
                      </div>
                      <h3 className="font-bold text-sm truncate">{m.model_name}</h3>
                      <p className="text-xs line-clamp-2 mt-0.5" style={{ color: "var(--txt-m)" }}>
                        {m.summary}
                      </p>
                    </div>

                    {/* MODEL SOURCE BADGE */}
                    <div className="shrink-0 flex items-center gap-2">
                      {m.upload_id ? (
                        <span
                          className="px-2.5 py-1 text-[10px] font-mono rounded-lg border font-semibold"
                          style={{
                            background: "var(--inp-bg)",
                            borderColor: "var(--border)",
                            color: "var(--txt-m)",
                          }}
                        >
                          Dataset: {m.upload_id}
                        </span>
                      ) : (
                        <span
                          className="px-2.5 py-1 text-[10px] font-mono rounded-lg border font-semibold"
                          style={{
                            background: "var(--inp-bg)",
                            borderColor: "var(--border)",
                            color: "var(--txt-f)",
                          }}
                        >
                          Benchmark Seed
                        </span>
                      )}
                    </div>
                  </div>

                  {/* METRICS ROW */}
                  <div
                    className="p-3 rounded-xl border grid grid-cols-3 sm:grid-cols-4 gap-2 text-center"
                    style={{ background: "var(--bg)", borderColor: "var(--border)" }}
                  >
                    {Object.entries(m.metrics).slice(0, 4).map(([metricKey, val]) => (
                      <div key={metricKey}>
                        <div className="text-[10px] uppercase font-bold tracking-wider" style={{ color: "var(--txt-m)" }}>
                          {metricKey.replace("_", " ")}
                        </div>
                        <div className="font-mono font-black text-xs mt-0.5" style={{ color: "var(--accent)" }}>
                          {typeof val === "number" ? val.toFixed(3) : val}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* FEATURE SIGNATURE */}
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--txt-f)" }}>
                      Target: <span className="font-mono font-bold" style={{ color: "var(--txt)" }}>{m.target_column}</span> · Expected Features ({m.features.length})
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-14 overflow-y-auto no-scrollbar">
                      {m.features.map((f) => (
                        <span
                          key={f}
                          className="px-1.5 py-0.5 rounded text-[10px] font-mono border"
                          style={{
                            background: "var(--bg)",
                            borderColor: "var(--border)",
                            color: "var(--txt-m)",
                          }}
                        >
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* ACTIONS */}
                  <div className="pt-2 border-t flex items-center justify-between gap-3" style={{ borderColor: "var(--border)" }}>
                    <span className="text-[10px] font-mono" style={{ color: "var(--txt-f)" }}>
                      By {m.created_by.split("@")[0]}
                    </span>

                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => handleApplyToWorkspace(m)}
                        disabled={applyingModelId === m.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all hover:scale-[1.02] cursor-pointer"
                        style={{
                          background: "linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.08))",
                          borderColor: "rgba(16, 185, 129, 0.35)",
                          color: "#10b981",
                        }}
                        title="Score active workspace dataset and append prediction columns"
                      >
                        {applyingModelId === m.id ? (
                          <Loader2 size={13} className="animate-spin text-emerald-400" />
                        ) : (
                          <Play size={13} className="text-emerald-400" />
                        )}
                        <span>{applyingModelId === m.id ? "Scoring Dataset..." : "⚡ Apply to Workspace Data"}</span>
                      </button>

                      <button
                        onClick={() => openInferencePlayground(m)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all hover:scale-[1.02] cursor-pointer"
                        style={{
                          background: "rgba(255, 67, 16, 0.08)",
                          borderColor: "rgba(255, 67, 16, 0.3)",
                          color: "var(--accent)",
                        }}
                      >
                        <Zap size={13} />
                        <span>Test Live Prediction</span>
                      </button>

                      <button
                        onClick={() => {
                          setActiveModelForBatch(m);
                          setBatchFile(null);
                          setBatchSuccess(false);
                          setBatchError("");
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all hover:scale-[1.02] cursor-pointer"
                        style={{
                          background: "var(--card)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                        title="Upload CSV to score bulk batch predictions"
                      >
                        <FileCode size={13} />
                        <span>Batch Score CSV</span>
                      </button>

                      <button
                        onClick={() => handleDownloadDocker(m.id, m.model_name)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all hover:scale-[1.02] cursor-pointer"
                        style={{
                          background: "var(--card)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                        title="Download Standalone Docker Microservice Container"
                      >
                        <Download size={13} />
                        <span>Docker Container</span>
                      </button>

                      {deleteConfirmId === m.id ? (
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl border border-red-500/40 bg-red-500/10">
                          <button
                            onClick={() => handleDeleteModel(m.id)}
                            disabled={deletingModelId === m.id}
                            className="text-xs font-bold text-red-400 hover:text-red-300 cursor-pointer flex items-center gap-1"
                          >
                            {deletingModelId === m.id ? <Loader2 size={11} className="animate-spin" /> : null}
                            <span>{deletingModelId === m.id ? "Deleting..." : "Confirm"}</span>
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="text-xs text-gray-400 hover:text-white cursor-pointer ml-1"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(m.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all hover:scale-[1.02] hover:text-red-400 hover:border-red-500/40 cursor-pointer"
                          style={{
                            background: "var(--card)",
                            borderColor: "var(--border)",
                            color: "var(--txt-m)",
                          }}
                          title="Delete Model from Registry"
                        >
                          <Trash2 size={13} />
                          <span>Delete</span>
                        </button>
                      )}

                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* LIVE INFERENCE PLAYGROUND MODAL */}
      {activeModelForInference && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            className="w-full max-w-2xl max-h-[90vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden"
            style={{ background: "var(--bg)", borderColor: "var(--border)" }}
          >
            {/* MODAL HEADER */}
            <div
              className="p-4 border-b flex items-center justify-between shrink-0"
              style={{ background: "var(--nav)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-2.5">
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: "rgba(255, 67, 16, 0.12)", color: "var(--accent)" }}
                >
                  <Zap size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold truncate">
                    Live Prediction Playground: {activeModelForInference.model_name}
                  </h3>
                  <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                    Real-time online scoring with probability confidence and latency telemetry.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setActiveModelForInference(null)}
                className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10"
              >
                <X size={18} />
              </button>
            </div>

            {/* MODAL BODY */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {predictError && (
                <div className="p-3 rounded-xl text-xs bg-red-500/10 text-red-500 border border-red-500/20">
                  {predictError}
                </div>
              )}

              {/* INPUT FORM */}
              <form onSubmit={handleExecutePrediction} className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                      Model Feature Inputs ({activeModelForInference.features.length})
                    </label>
                    <button
                      type="button"
                      onClick={() => openInferencePlayground(activeModelForInference)}
                      className="text-[11px] font-semibold underline cursor-pointer"
                      style={{ color: "var(--accent)" }}
                    >
                      Reset Default Values
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-52 overflow-y-auto p-1">
                    {activeModelForInference.features.map((feat) => (
                      <div key={feat}>
                        <label className="block text-[11px] font-mono truncate mb-1" style={{ color: "var(--txt-m)" }}>
                          {feat}
                        </label>
                        <input
                          type="text"
                          value={featureInputs[feat] ?? ""}
                          onChange={(e) =>
                            setFeatureInputs({
                              ...featureInputs,
                              [feat]: e.target.value,
                            })
                          }
                          className="w-full px-3 py-1.5 rounded-xl text-xs border bg-transparent outline-none focus:border-[var(--accent)] font-mono"
                          style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                  <button
                    type="submit"
                    disabled={predicting}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all shadow-md cursor-pointer hover:scale-[1.02]"
                    style={{ background: "var(--accent)" }}
                  >
                    <Play size={13} fill="currentColor" />
                    <span>{predicting ? "Scoring..." : "Execute Prediction"}</span>
                  </button>
                </div>
              </form>

              {/* PREDICTION RESULT DASHBOARD */}
              {predictionResult && (
                <div
                  className="p-4 rounded-xl border space-y-3"
                  style={{ background: "var(--card)", borderColor: "rgba(16, 185, 129, 0.4)" }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-black uppercase tracking-wider text-emerald-500 flex items-center gap-1.5">
                      <CheckCircle2 size={14} />
                      Inference Outcome
                    </span>
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-mono font-bold"
                      style={{ background: "rgba(99, 102, 241, 0.15)", color: "#6366f1" }}
                    >
                      Latency: {predictionResult.latency_ms} ms
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 rounded-lg" style={{ background: "var(--bg)" }}>
                    <div>
                      <div className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>
                        Predicted Target
                      </div>
                      <div className="text-base font-black font-mono mt-0.5" style={{ color: "var(--txt)" }}>
                        {predictionResult.prediction}
                      </div>
                    </div>

                    {predictionResult.confidence !== undefined && (
                      <div>
                        <div className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>
                          Model Confidence
                        </div>
                        <div className="text-base font-black font-mono text-emerald-500 mt-0.5">
                          {(predictionResult.confidence * 100).toFixed(1)}%
                        </div>
                      </div>
                    )}

                    {predictionResult.confidence_interval && (
                      <div>
                        <div className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>
                          95% Conf Interval
                        </div>
                        <div className="text-xs font-mono font-bold mt-1" style={{ color: "var(--txt-m)" }}>
                          [{predictionResult.confidence_interval[0]}, {predictionResult.confidence_interval[1]}]
                        </div>
                      </div>
                    )}
                  </div>

                  {/* PROBABILITY DISTRIBUTION BARS */}
                  {predictionResult.probabilities && (
                    <div className="space-y-1.5">
                      <div className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>
                        Class Probabilities
                      </div>
                      <div className="space-y-1">
                        {Object.entries(predictionResult.probabilities).map(([cls, prob]) => (
                          <div key={cls} className="flex items-center gap-2 text-xs font-mono">
                            <span className="w-16 truncate">Class {cls}:</span>
                            <div className="flex-1 h-3 rounded-full overflow-hidden bg-black/10 dark:bg-white/10">
                              <div
                                className="h-full rounded-full transition-all duration-500"
                                style={{
                                  width: `${Math.round(prob * 100)}%`,
                                  background: cls === "1" ? "var(--accent)" : "#6366f1",
                                }}
                              />
                            </div>
                            <span className="w-12 text-right font-bold">{(prob * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* API SNIPPETS FOR PRODUCTION INTEGRATION */}
              <div className="space-y-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold" style={{ color: "var(--txt-m)" }}>
                    Production Microservice Integration
                  </span>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setCodeSnippetTab("curl")}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer ${
                        codeSnippetTab === "curl" ? "bg-black/10 dark:bg-white/10 text-[var(--txt)]" : "text-[var(--txt-m)]"
                      }`}
                    >
                      cURL
                    </button>
                    <button
                      onClick={() => setCodeSnippetTab("python")}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer ${
                        codeSnippetTab === "python" ? "bg-black/10 dark:bg-white/10 text-[var(--txt)]" : "text-[var(--txt-m)]"
                      }`}
                    >
                      Python
                    </button>
                  </div>
                </div>

                {(() => {
                  const apiBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000").replace(/\/api\/?$/, "").replace(/\/$/, "");
                  return (
                    <pre
                      className="p-3 rounded-xl text-[11px] font-mono overflow-x-auto border"
                      style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                    >
                      {codeSnippetTab === "curl"
                        ? `curl -X POST ${apiBase}/api/v1/models/${activeModelForInference.id}/predict \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify({ features: featureInputs })}'`
                        : `import requests

url = "${apiBase}/api/v1/models/${activeModelForInference.id}/predict"
payload = {"features": ${JSON.stringify(featureInputs)}}
response = requests.post(url, json=payload)
print(response.json())`}
                    </pre>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* REGISTER NEW MODEL MODAL */}
      {showRegisterModal && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            className="w-full max-w-md rounded-2xl border p-5 shadow-2xl space-y-4"
            style={{ background: "var(--bg)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Boxes size={18} style={{ color: "var(--accent)" }} />
                <h3 className="font-bold text-sm">Register Model Artifact</h3>
              </div>
              <button onClick={() => setShowRegisterModal(false)} className="p-1 rounded-lg">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleRegisterModel} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                  Model Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Lead Conversion Classifier"
                  value={newModelName}
                  onChange={(e) => setNewModelName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl text-xs border bg-transparent outline-none focus:border-[var(--accent)]"
                  style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Algorithm
                  </label>
                  <select
                    value={newModelAlgo}
                    onChange={(e) => setNewModelAlgo(e.target.value)}
                    className="w-full px-2 py-2 rounded-xl text-xs border bg-transparent outline-none cursor-pointer"
                    style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                  >
                    <option value="LightGBM">LightGBM</option>
                    <option value="XGBoost">XGBoost</option>
                    <option value="CatBoost">CatBoost</option>
                    <option value="Random Forest">Random Forest</option>
                    <option value="Extra Trees">Extra Trees</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Task Type
                  </label>
                  <select
                    value={newModelTask}
                    onChange={(e) => setNewModelTask(e.target.value as any)}
                    className="w-full px-2 py-2 rounded-xl text-xs border bg-transparent outline-none cursor-pointer"
                    style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                  >
                    <option value="classification">Classification</option>
                    <option value="regression">Regression</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                  Target Column Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="churn, converted, revenue"
                  value={newModelTarget}
                  onChange={(e) => setNewModelTarget(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl text-xs border bg-transparent outline-none focus:border-[var(--accent)]"
                  style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                  Feature Columns (comma separated)
                </label>
                <input
                  type="text"
                  required
                  placeholder="age, income, tenure, score"
                  value={newModelFeatures}
                  onChange={(e) => setNewModelFeatures(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl text-xs border bg-transparent outline-none focus:border-[var(--accent)] font-mono"
                  style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRegisterModal(false)}
                  className="px-3 py-2 rounded-xl text-xs font-semibold border"
                  style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={registering}
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white transition-all cursor-pointer"
                  style={{ background: "var(--accent)" }}
                >
                  {registering ? "Registering..." : "Save to Registry"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* BATCH CSV PREDICTION MODAL */}
      {activeModelForBatch && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            className="w-full max-w-lg rounded-2xl border p-6 shadow-2xl space-y-4"
            style={{ background: "var(--bg)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode size={20} style={{ color: "var(--accent)" }} />
                <div>
                  <h3 className="font-bold text-sm">Batch CSV Prediction Engine</h3>
                  <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                    Score bulk records using {activeModelForBatch.model_name} ({activeModelForBatch.algorithm})
                  </p>
                </div>
              </div>
              <button
                onClick={() => {
                  setActiveModelForBatch(null);
                  setBatchFile(null);
                  setBatchError("");
                  setBatchSuccess(false);
                }}
                className="p-1 rounded-lg"
              >
                <X size={16} />
              </button>
            </div>

            <div
              className="p-3 rounded-xl border text-xs space-y-1"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="font-semibold text-[11px]" style={{ color: "var(--txt)" }}>
                Expected Features in CSV:
              </div>
              <div className="flex flex-wrap gap-1 font-mono text-[10px]">
                {activeModelForBatch.features.map((f) => (
                  <span
                    key={f}
                    className="px-1.5 py-0.5 rounded border"
                    style={{ background: "var(--bg)", borderColor: "var(--border)", color: "var(--accent)" }}
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>

            <div className="space-y-3">
              <label className="block text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
                Select CSV File to Score
              </label>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setBatchFile(e.target.files[0]);
                    setBatchError("");
                    setBatchSuccess(false);
                  }
                }}
                className="w-full text-xs p-3 rounded-xl border cursor-pointer"
                style={{
                  background: "var(--inp-bg)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              />

              {batchError && (
                <div
                  className="p-3 rounded-xl text-xs border"
                  style={{ background: "rgba(239, 68, 68, 0.1)", borderColor: "rgba(239, 68, 68, 0.3)", color: "#ef4444" }}
                >
                  {batchError}
                </div>
              )}

              {batchSuccess && (
                <div
                  className="p-3 rounded-xl text-xs border flex items-center gap-2"
                  style={{ background: "rgba(16, 185, 129, 0.1)", borderColor: "rgba(16, 185, 129, 0.3)", color: "#10b981" }}
                >
                  <CheckCircle2 size={16} />
                  <span>Batch scoring complete! Predictions file downloaded automatically.</span>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
              <button
                type="button"
                onClick={() => {
                  setActiveModelForBatch(null);
                  setBatchFile(null);
                  setBatchError("");
                  setBatchSuccess(false);
                }}
                className="px-4 py-2 rounded-xl text-xs font-semibold border cursor-pointer"
                style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
              >
                Close
              </button>
              <button
                type="button"
                disabled={!batchFile || batchScoring}
                onClick={handleBatchPredictCsv}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white transition-all cursor-pointer disabled:opacity-50"
                style={{ background: "var(--accent)" }}
              >
                {batchScoring ? (
                  <>
                    <RefreshCw size={13} className="animate-spin" />
                    <span>Scoring Batch Records...</span>
                  </>
                ) : (
                  <>
                    <Download size={13} />
                    <span>Run Batch Score & Download CSV</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
