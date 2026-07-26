"use client";

import React, { useState, useEffect } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";

export function AutoMLTab() {
  const { profile, activeTab, uploadId } = useWorkspace();
  const [automlTarget, setAutomlTarget] = useState("");
  const [automlTask, setAutomlTask] = useState("auto");
  const [automlTimeBudget, setAutomlTimeBudget] = useState("60");
  const [automlTestSize, setAutomlTestSize] = useState("20");

  const [profileCols, setProfileCols] = useState<string[]>([]);
  const [detectedTask, setDetectedTask] = useState("");
  const [detectedNUnique, setDetectedNUnique] = useState(0);

  const [isTraining, setIsTraining] = useState(false);
  const [automlError, setAutomlError] = useState("");
  const [automlResult, setAutomlResult] = useState<any>(null);

  useEffect(() => {
    if (automlTarget) {
      detectTask();
    }
  }, [automlTarget]);

  const detectTask = async () => {
    if (!automlTarget) return;
    try {
      const res = await apiFetch("/automl/detect-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_col: automlTarget, upload_id: uploadId }),
      });
      if (!res.ok) return;
      const data = await res.json();

      if (data.needs_selection) {
        if (data.columns && data.columns.length) {
          setProfileCols(data.columns);
        }
        setAutomlTarget("");
        setDetectedTask("");
        setDetectedNUnique(0);
        return;
      }

      setDetectedTask(data.task);
      setDetectedNUnique(data.n_unique);
    } catch (e) {}
  };

  const runAutoml = async () => {
    if (!automlTarget) return;
    setIsTraining(true);
    setAutomlError("");
    setAutomlResult(null);

    try {
      const res = await apiFetch("/automl/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_col: automlTarget,
          task_choice: automlTask,
          time_budget: parseInt(automlTimeBudget),
          test_size: parseInt(automlTestSize),
          upload_id: uploadId
        }),
      });

      if (!res.ok) {
        let errStr = "AutoML failed.";
        try {
          const data = await res.json();
          if (data.error) errStr = data.error;
        } catch (e) {}
        setAutomlError(errStr);
        setIsTraining(false);
        return;
      }

      const data = await res.json();
      if (data.error) {
        setAutomlError(data.error);
        setIsTraining(false);
        return;
      }

      if (data.sync || !data.task_id) {
        setAutomlResult({
          metrics: {},
          leaderboard: [],
          feature_importance: [],
          shap_summary: [],
          ...data,
        });
        if (data.target_col) setAutomlTarget(data.target_col);
        setIsTraining(false);
        return;
      }

      // Handle async polling if needed (simplification here assumes sync response or polling handled elsewhere)
      // Original logic polled `/api/tasks/status/...`.
      const pollTask = async (taskId: string) => {
        while (true) {
          await new Promise(r => setTimeout(r, 2000));
          const pRes = await apiFetch(`/tasks/status/${taskId}`);
          if (!pRes.ok) throw new Error("Task check failed");
          const pData = await pRes.json();
          if (pData.status === "completed") {
            return pData.result;
          }
          if (pData.status === "failed") {
            throw new Error(pData.error || "Training failed");
          }
        }
      };

      const result = await pollTask(data.task_id);
      setAutomlResult(result);
    } catch (e: any) {
      setAutomlError(String(e.message || e));
    } finally {
      setIsTraining(false);
    }
  };

  const allColumns = profile?.columns?.map((c: any) => c.name) || profileCols;

  return (
    <div className="tab-panel space-y-5 px-4 py-4 md:px-6 md:py-6">
      <div className="sec-hd flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
            AutoML
          </h2>
          <p className="sec-sub text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>
            FLAML · Auto-detect task · Leaderboard · Model export
          </p>
        </div>
        {automlResult && (
          <a href="/api/automl/download" className="bg" style={{ textDecoration: "none" }}>↓ DOWNLOAD MODEL (.pkl)</a>
        )}
      </div>

      <div className="grid-1-3 grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="sl block mb-2">Target Column</label>
          <select value={automlTarget} onChange={e => setAutomlTarget(e.target.value)} className="inp w-full" style={{ padding: ".5rem .8rem", borderRadius: ".5rem", background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
            <option value="">- select target -</option>
            {allColumns.map((col: string) => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
          {detectedTask && (
            <p className="mt-2 text-[10px] font-bold px-2 py-1 rounded inline-block" style={{ background: "rgba(46,91,255,.1)", color: "var(--accent)" }}>
              Detected: {detectedTask} ({detectedNUnique} unique)
            </p>
          )}
        </div>
        <div>
          <label className="sl block mb-2">Task Override</label>
          <select value={automlTask} onChange={e => setAutomlTask(e.target.value)} className="inp w-full" style={{ padding: ".5rem .8rem", borderRadius: ".5rem", background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
            <option value="auto">Auto (from Target)</option>
            <option value="classification">Classification</option>
            <option value="regression">Regression</option>
          </select>
        </div>
        <div>
          <label className="sl block mb-2">Time Budget (sec)</label>
          <select value={automlTimeBudget} onChange={e => setAutomlTimeBudget(e.target.value)} className="inp w-full" style={{ padding: ".5rem .8rem", borderRadius: ".5rem", background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
            <option value="15">15 seconds (Demo)</option>
            <option value="60">60 seconds (Quick)</option>
            <option value="300">5 minutes (Standard)</option>
            <option value="900">15 minutes (Deep)</option>
          </select>
        </div>
        <div>
          <label className="sl block mb-2">Test Size (%)</label>
          <select value={automlTestSize} onChange={e => setAutomlTestSize(e.target.value)} className="inp w-full" style={{ padding: ".5rem .8rem", borderRadius: ".5rem", background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
            <option value="10">10%</option>
            <option value="20">20%</option>
            <option value="30">30%</option>
          </select>
        </div>
      </div>

      <div className="flex justify-end border-t pt-4" style={{ borderColor: "var(--border)" }}>
        <button onClick={runAutoml} disabled={isTraining || !automlTarget} className={`bp ${!automlTarget || isTraining ? 'opacity-50 cursor-not-allowed' : ''}`}>
          {isTraining && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>}
          <span>{isTraining ? 'TRAINING...' : 'START AUTOML'}</span>
        </button>
      </div>

      {automlError && (
        <div className="p-4 rounded-xl space-y-1 mt-4" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>
          <p className="font-bold text-sm text-red-400">⚠ AutoML Error</p>
          <p className="font-mono text-xs text-red-400 mt-1">{automlError}</p>
        </div>
      )}

      {isTraining && (
        <div className="gc p-8 rounded-2xl flex flex-col items-center justify-center gap-4 text-center mt-4">
          <div className="ld2" style={{ background: "var(--accent)" }}></div>
          <div>
            <p className="font-bold text-sm">FLAML is evaluating models...</p>
            <p className="text-[10px] mt-1" style={{ color: "var(--txt-m)" }}>This will take ~{automlTimeBudget} seconds.</p>
          </div>
        </div>
      )}

      {automlResult && !isTraining && (
        <div className="space-y-4 mt-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(automlResult.metrics || {}).map(([k, v]: [string, any]) => (
              <div key={k} className="gc p-4 rounded-xl">
                <p className="sl">{k}</p>
                <p className="text-xl font-black mt-1" style={{ color: "var(--accent)" }}>{typeof v === 'number' ? v.toFixed(4) : v}</p>
              </div>
            ))}
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="gc rounded-xl p-4">
              <h3 className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--txt-m)" }}>Model Leaderboard</h3>
              <div className="tbl-scroll">
                <table className="dt w-full">
                  <thead><tr><th>Model</th><th>Metric</th><th>Config</th></tr></thead>
                  <tbody>
                    {(automlResult.leaderboard || []).map((row: any, i: number) => (
                      <tr key={i} style={{ borderLeft: row.best ? '2px solid var(--accent)' : 'none' }}>
                        <td>
                          {row.best && <span className="text-amber-400 mr-1">★</span>}
                          <span className="font-mono font-bold" style={{ color: row.best ? 'var(--accent)' : 'var(--txt)' }}>{row.model}</span>
                        </td>
                        <td className="font-mono">{row.metric ?? '-'}</td>
                        <td className="font-mono text-[10px] max-w-[150px] truncate">{row.best_config ?? '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {automlResult.feature_importance && automlResult.feature_importance.length > 0 && (
              <div className="gc rounded-xl p-4">
                <h3 className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--txt-m)" }}>Feature Importance (Top 15)</h3>
                <div className="space-y-2.5">
                  {automlResult.feature_importance.map((fi: any, i: number) => {
                    const maxImp = automlResult.feature_importance[0].importance;
                    const pct = maxImp > 0 ? Math.max(1, (fi.importance / maxImp) * 100) : 1;
                    return (
                      <div key={fi.feature} className="flex items-center gap-2">
                        <span className="text-[10px] w-24 truncate text-right font-medium">{fi.feature}</span>
                        <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                          <div className="h-full rounded-full" style={{ background: "var(--accent)", width: `${pct}%` }}></div>
                        </div>
                        <span className="text-[9px] font-mono w-12 text-right" style={{ color: "var(--txt-m)" }}>{Number(fi.importance).toFixed(4)}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
