"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useWorkspace } from "./WorkspaceProvider";
import {
  Boxes,
  Download,
  RefreshCw,
  Search,
  Trash2,
  Loader2,
  Calendar,
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

export function ModelRegistryTab() {
  const [models, setModels] = useState<ModelRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [taskFilter, setTaskFilter] = useState<"all" | "classification" | "regression">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Deletion state
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deletingModelId, setDeletingModelId] = useState<string | null>(null);

  // Fetch model catalog
  const fetchModels = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch("/models");
      if (res.ok) {
        const data = await res.json();
        setModels(Array.isArray(data) ? data : data.models || []);
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

  const handleDeleteModel = async (modelId: string) => {
    setDeletingModelId(modelId);
    try {
      const res = await apiFetch(`/models/${modelId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setModels((prev) => prev.filter((m) => m.id !== modelId));
      }
    } catch (e) {
      console.error("Failed to delete model:", e);
    } finally {
      setDeletingModelId(null);
      setDeleteConfirmId(null);
    }
  };

  const handleDownloadDocker = async (modelId: string, modelName: string) => {
    try {
      const res = await apiFetch(`/models/${modelId}/docker-export`);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `docker-${modelName.toLowerCase().replace(/\s+/g, "-")}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (e) {
      console.error("Failed to download docker artifact:", e);
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
            <h1 className="text-base font-bold">Enterprise Model Registry</h1>
            <p className="text-xs" style={{ color: "var(--txt-m)" }}>
              AutoML-trained model catalog — view metrics and download artifacts.
            </p>
          </div>
        </div>

        {/* METRICS SUMMARY */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <div
            className="px-3 py-1.5 rounded-lg border flex items-center gap-2 text-xs font-mono"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <span style={{ color: "var(--txt-m)" }}>Catalog:</span>
            <span className="font-bold">{models.length} Models</span>
          </div>

          <div
            className="px-3 py-1.5 rounded-lg border flex items-center gap-2 text-xs font-mono"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <span style={{ color: "var(--txt-m)" }}>Classification:</span>
            <span className="font-bold text-indigo-500">{classificationCount}</span>
          </div>

          <div
            className="px-3 py-1.5 rounded-lg border flex items-center gap-2 text-xs font-mono"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <span style={{ color: "var(--txt-m)" }}>Regression:</span>
            <span className="font-bold text-cyan-500">{regressionCount}</span>
          </div>

          <button
            onClick={fetchModels}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold transition-all hover:scale-[1.02] cursor-pointer"
            style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
            title="Reload model catalog"
          >
            <RefreshCw size={13} className={loading ? "animate-spin text-indigo-500" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* FILTER & SEARCH TOOLBAR */}
      <div
        className="shrink-0 px-4 py-2.5 border-b flex items-center justify-between gap-4 flex-wrap"
        style={{ background: "var(--bg)", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-1 p-0.5 rounded-lg border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          {(["all", "classification", "regression"] as const).map((task) => (
            <button
              key={task}
              onClick={() => setTaskFilter(task)}
              className={`px-3 py-1 rounded-md text-xs font-bold capitalize transition-colors cursor-pointer ${
                taskFilter === task
                  ? "bg-[var(--surface)] text-[var(--txt)] shadow-sm border border-[var(--border)]"
                  : "text-[var(--txt-m)] hover:text-[var(--txt)]"
              }`}
            >
              {task === "all" ? "All Models" : task}
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
              <p className="font-bold text-sm" style={{ color: "var(--txt)" }}>No models found in catalog</p>
              <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
                Run an AutoML training tournament to register models and artifacts.
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
                      <div className="flex items-center gap-2 flex-wrap mb-1.5">
                        <span
                          className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider"
                          style={{
                            background: "var(--inp-bg)",
                            color: "var(--accent)",
                            border: "1px solid var(--border)",
                          }}
                        >
                          {m.algorithm}
                        </span>
                        <span
                          className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold uppercase tracking-wider"
                          style={{
                            background: "var(--inp-bg)",
                            color: "var(--txt-m)",
                            border: "1px solid var(--border)",
                          }}
                        >
                          {m.task_type}
                        </span>
                        <span className="font-mono text-[10px]" style={{ color: "var(--txt-f)" }}>
                          v{m.version || "1.0"}
                        </span>
                      </div>
                      <h3 className="font-bold text-sm truncate" style={{ color: "var(--txt)" }}>{m.model_name}</h3>
                      <p className="text-xs line-clamp-2 mt-0.5" style={{ color: "var(--txt-m)" }}>
                        {m.summary || `AutoML ${m.algorithm} model trained on target '${m.target_column}'.`}
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
                          AutoML Artifact
                        </span>
                      )}
                    </div>
                  </div>

                  {/* METRICS ROW */}
                  <div
                    className="p-3 rounded-xl border grid grid-cols-3 sm:grid-cols-4 gap-2 text-center"
                    style={{ background: "var(--bg)", borderColor: "var(--border)" }}
                  >
                    {Object.entries(m.metrics || {}).slice(0, 4).map(([metricKey, val]) => (
                      <div key={metricKey}>
                        <div className="text-[10px] uppercase font-bold tracking-wider" style={{ color: "var(--txt-m)" }}>
                          {metricKey.replace(/_/g, " ")}
                        </div>
                        <div className="font-mono font-black text-xs mt-0.5" style={{ color: "var(--accent)" }}>
                          {typeof val === "number" ? val.toFixed(3) : (val !== null && val !== undefined ? String(val) : "N/A")}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* FEATURE SIGNATURE */}
                  <div>
                    <div className="text-[10px] font-bold uppercase tracking-wider mb-1.5" style={{ color: "var(--txt-f)" }}>
                      Target: <span className="font-mono font-bold" style={{ color: "var(--txt)" }}>{m.target_column}</span> · Expected Features ({(m.features || []).length})
                    </div>
                    <div className="flex flex-wrap gap-1 max-h-14 overflow-y-auto no-scrollbar">
                      {(m.features || []).map((f) => (
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
                  <div className="pt-3 border-t flex items-center justify-between gap-3" style={{ borderColor: "var(--border)" }}>
                    <span className="text-[10px] font-mono flex items-center gap-1.5" style={{ color: "var(--txt-f)" }}>
                      <Calendar size={11} />
                      {m.created_at ? new Date(m.created_at).toLocaleDateString() : "Catalog Artifact"}
                    </span>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDownloadDocker(m.id, m.model_name)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold transition-all hover:scale-[1.02] cursor-pointer"
                        style={{
                          background: "var(--surface)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                        title="Download Standalone Docker Microservice Container"
                      >
                        <Download size={13} className="text-indigo-500" />
                        <span>Docker Container</span>
                      </button>

                      {deleteConfirmId === m.id ? (
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-red-500/40 bg-red-500/10">
                          <button
                            onClick={() => handleDeleteModel(m.id)}
                            disabled={deletingModelId === m.id}
                            className="text-xs font-bold text-red-500 hover:text-red-600 cursor-pointer flex items-center gap-1"
                          >
                            {deletingModelId === m.id ? <Loader2 size={11} className="animate-spin" /> : null}
                            <span>{deletingModelId === m.id ? "Deleting..." : "Confirm Delete?"}</span>
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="text-xs opacity-60 hover:opacity-100 cursor-pointer ml-1"
                            style={{ color: "var(--txt)" }}
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(m.id)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold transition-all hover:scale-[1.02] hover:text-red-500 hover:border-red-500/40 cursor-pointer"
                          style={{
                            background: "var(--surface)",
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
    </div>
  );
}
