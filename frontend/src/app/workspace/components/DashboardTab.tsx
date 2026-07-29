"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { RefreshCw, X, BarChart4, TrendingUp, TrendingDown, Minus, Plus, Layers, PieChart, Activity, GitBranch } from "lucide-react";
import { Scatter, Line, Bar, Pie, Doughnut } from "react-chartjs-2";
import { ForecastCard } from "./InsightsTab";

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Title, Tooltip, Legend, Filler
);

const PALETTE = [
  "#6366f1","#10b981","#f59e0b","#ef4444","#8b5cf6",
  "#06b6d4","#ec4899","#f97316","#84cc16","#14b8a6",
  "#3b82f6","#a78bfa","#34d399","#fbbf24","#f87171",
];

const CHART_TYPES = [
  { id: "bar",      label: "Bar",      icon: "bar" },
  { id: "line",     label: "Line / Time Series", icon: "line" },
  { id: "scatter",  label: "Scatter",  icon: "scatter" },
  { id: "pie",      label: "Pie",      icon: "pie" },
  { id: "doughnut", label: "Donut",    icon: "donut" },
  { id: "boxplot",  label: "Box Plot", icon: "box" },
];

function fmtNum(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000)     return `${(v / 1_000).toFixed(1)}K`;
  return v % 1 === 0 ? String(v) : v.toFixed(2);
}

// ── Box Plot ──────────────────────────────────────────────────────────────────
function BoxPlotViz({ data, formatted, xLabel = "Category", yLabel = "Value" }: { data: any; formatted: any; xLabel?: string; yLabel?: string }) {
  if (!data || typeof data.min !== "number") return (
    <p className="text-xs text-center py-10 font-medium text-slate-700">Invalid data</p>
  );
  const range = data.max - data.min;
  const pad   = range === 0 ? 1 : range * 0.12;
  const minX  = data.min - pad;
  const total = (data.max + pad) - minX;
  const toPct = (v: number) => `${Math.max(0, Math.min(100, ((v - minX) / total) * 100)).toFixed(2)}%`;
  return (
    <div className="w-full h-full flex flex-col justify-center px-4 select-none">
      <div className="text-center mb-1 font-bold text-xs text-black uppercase tracking-wider">{toLabel(xLabel)} Distribution ({toLabel(yLabel)})</div>
      <div className="relative w-full h-14 flex items-center mb-8 mt-2">
        <div className="absolute h-0.5 bg-slate-400" style={{ left: toPct(data.min), right: `${(100 - parseFloat(toPct(data.max))).toFixed(2)}%` }} />
        <div className="absolute w-1 h-5 rounded bg-slate-600" style={{ left: toPct(data.min), top: "50%", transform: "translate(-50%,-50%)" }} />
        <div className="absolute w-1 h-5 rounded bg-slate-600" style={{ left: toPct(data.max), top: "50%", transform: "translate(-50%,-50%)" }} />
        <div className="absolute h-9 rounded-md" style={{ left: toPct(data.q1), width: `${((data.q3 - data.q1) / total) * 100}%`, background: "rgba(99,102,241,0.25)", border: "2px solid #6366f1", top: "50%", transform: "translateY(-50%)" }} />
        <div className="absolute w-1 h-10 rounded bg-amber-500 shadow-md" style={{ left: toPct(data.median), top: "50%", transform: "translate(-50%,-50%)" }} />
        <div className="absolute text-[10px] font-bold font-mono -bottom-6 text-center text-slate-900" style={{ left: toPct(data.min), transform: "translateX(-50%)" }}>{formatted?.min}</div>
        <div className="absolute text-[10px] font-bold font-mono -bottom-6 text-center text-slate-900" style={{ left: toPct(data.max), transform: "translateX(-50%)" }}>{formatted?.max}</div>
        <div className="absolute text-[11px] font-black font-mono -top-7 text-center text-amber-700" style={{ left: toPct(data.median), transform: "translateX(-50%)" }}>{formatted?.median}</div>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2">
        {([["Q1", formatted?.q1, "#4f46e5"], ["Median", formatted?.median, "#d97706"], ["Q3", formatted?.q3, "#4f46e5"]] as [string,string,string][]).map(([lbl, val, col]) => (
          <div key={lbl} className="text-center rounded-lg py-1.5 bg-slate-100 border border-slate-300">
            <p className="text-[9px] uppercase tracking-widest font-extrabold text-slate-700 mb-0.5">{lbl}</p>
            <p className="text-xs font-black font-mono" style={{ color: col }}>{val}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── KPI Card ──────────────────────────────────────────────────────────────────
function KpiCard({ stat, idx }: { stat: any; idx: number }) {
  const color = stat.color || PALETTE[idx % PALETTE.length];
  return (
    <div className="relative overflow-hidden rounded-2xl p-5 flex flex-col justify-between" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.07)", minHeight: 110 }}>
      <div className="absolute -top-8 -right-8 w-24 h-24 rounded-full opacity-15 blur-2xl pointer-events-none" style={{ background: color }} />
      <div className="flex items-start justify-between">
        <p className="text-[10px] font-bold uppercase tracking-widest truncate pr-2" style={{ color: "var(--txt-m)" }}>{stat.label}</p>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${color}22`, color }}>
          <BarChart4 size={14} />
        </div>
      </div>
      <div>
        <p className="text-3xl font-black tracking-tight mt-2" style={{ color }}>{stat.value}</p>
        {stat.sub && <p className="text-[10px] font-semibold mt-1 truncate" style={{ color: "rgba(255,255,255,0.4)" }}>{stat.sub}</p>}
      </div>
    </div>
  );
}

// helpers
const toLabel = (s: string) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());

// ── Chart renderer ─────────────────────────────────────────────────────────────
function renderChart(ch: any, idx: number) {
  const color  = PALETTE[idx % PALETTE.length];
  const xLabel = toLabel(ch.x_col || "Category");
  const agg    = ch.agg_type && ch.agg_type !== "none" ? ` (${ch.agg_type})` : "";
  const yLabel = toLabel(ch.y_col || "Count") + agg;

  const tooltip = {
    callbacks: {
      title:  (items: any[]) => `${xLabel}: ${items[0]?.label ?? ""}`,
      label:  (ctx: any) => {
        const v = ctx.parsed?.y ?? ctx.raw;
        if (typeof v === "number") return `  ${yLabel}: ${fmtNum(v)}`;
        if (v && typeof v.y === "number") return `  ${yLabel}: ${fmtNum(v.y)}`;
        return `  ${v}`;
      },
    },
    displayColors:   false,
    backgroundColor: "rgba(8,8,18,0.97)",
    borderColor:     "rgba(255,255,255,0.15)",
    borderWidth:     1,
    titleColor:      "rgba(255,255,255,0.95)",
    bodyColor:       "rgba(255,255,255,0.75)",
    padding:         12,
    cornerRadius:    10,
  };

  const scales: any = {
    x: {
      title: {
        display: true,
        text:    xLabel,
        color:   "#000000",
        font:    { size: 12, weight: "bold", family: "inherit" },
        padding: { top: 6 },
      },
      ticks: {
        color:        "#000000",
        font:         { size: 11, weight: "bold" },
        maxTicksLimit: 10,
        maxRotation:  30,
        autoSkip:     true,
      },
      grid:   { color: "rgba(0,0,0,0.08)" },
      border: { color: "#000000" },
    },
    y: {
      title: {
        display: true,
        text:    yLabel,
        color:   "#000000",
        font:    { size: 12, weight: "bold", family: "inherit" },
        padding: { bottom: 6 },
      },
      ticks: {
        color:         "#000000",
        font:          { size: 11, weight: "bold" },
        callback:      (v: any) => fmtNum(Number(v)),
        maxTicksLimit: 6,
      },
      grid:        { color: "rgba(0,0,0,0.08)" },
      border:      { color: "#000000" },
      beginAtZero: true,
    },
  };

  const common: any = {
    responsive:          true,
    maintainAspectRatio: false,
    animation:           { duration: 500 },
    layout:              { padding: { top: 4, right: 10, bottom: 4, left: 4 } },
    plugins:             { legend: { display: false }, tooltip },
    scales,
  };

  if (ch.type === "scatter") {
    const pts = Array.isArray(ch.values) && ch.values.length > 0 && typeof ch.values[0] === "object" && ch.values[0].x !== undefined
      ? ch.values
      : (ch.values || []).map((v: any, i: number) => ({ x: parseFloat(ch.labels?.[i]) || i, y: v }));
    return <Scatter
      data={{ datasets: [{ label: ch.title, data: pts, backgroundColor: `${color}99`, pointRadius: 5, pointHoverRadius: 8, pointBorderColor: color, pointBorderWidth: 1 }] }}
      options={{ ...common, scales: { ...scales, x: { ...scales.x, type: "linear" as const } } }}
    />;
  }

  if (ch.type === "line") {
    return <Line
      data={{ labels: ch.labels, datasets: [{ label: yLabel, data: ch.values, borderColor: color, backgroundColor: `${color}15`, borderWidth: 2.5, fill: true, tension: 0.35, pointRadius: 4, pointBackgroundColor: "#fff", pointBorderColor: color, pointBorderWidth: 2, pointHoverRadius: 7 }] }}
      options={common}
    />;
  }

  if (ch.type === "pie" || ch.type === "doughnut") {
    const Comp = ch.type === "doughnut" ? Doughnut : Pie;
    const total = (ch.values || []).reduce((s: number, v: number) => s + (Number(v) || 0), 0);
    return <Comp
      data={{ labels: ch.labels, datasets: [{ data: ch.values, backgroundColor: PALETTE, borderColor: "rgba(0,0,0,0.3)", borderWidth: 2, hoverOffset: 12 }] }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 500 },
        layout: { padding: { top: 10, bottom: 10, left: 10, right: 10 } },
        plugins: {
          legend: {
            display: true,
            position: "right" as const,
            labels: {
              color: "#000000",
              font: { size: 12, weight: "bold" },
              boxWidth: 14,
              padding: 14,
              generateLabels: (chart: any) => {
                const ds = chart.data.datasets[0];
                return (chart.data.labels || []).map((lbl: string, i: number) => {
                  const val = ds.data[i];
                  const pct = total > 0 ? ((Number(val) / total) * 100).toFixed(1) : "0";
                  return {
                    text: `${lbl} (${pct}%)`,
                    fillStyle: PALETTE[i % PALETTE.length],
                    strokeStyle: "rgba(0,0,0,0.3)",
                    lineWidth: 1,
                    index: i,
                    hidden: false,
                  };
                });
              },
            },
          },
          tooltip: {
            ...tooltip,
            callbacks: {
              label: (ctx: any) => {
                const val = Number(ctx.parsed);
                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : "0";
                return `  ${ctx.label}: ${fmtNum(val)} (${pct}%)`;
              },
            },
          },
        },
      }}
    />;
  }

  // Bar / histogram — per-bar palette colours
  return <Bar
    data={{
      labels: ch.labels,
      datasets: [{
        label:           yLabel,
        data:            ch.values,
        backgroundColor: (ch.labels || []).map((_: any, i: number) => `${PALETTE[i % PALETTE.length]}cc`),
        borderColor:     (ch.labels || []).map((_: any, i: number) => PALETTE[i % PALETTE.length]),
        borderWidth:     1.5,
        borderRadius:    6,
        borderSkipped:   false as const,
      }],
    }}
    options={{
      ...common,
      scales: {
        ...scales,
        x: {
          ...scales.x,
          ticks: {
            color:         "#000000",
            font:          { size: 11, weight: "bold" },
            maxRotation:   45,
            minRotation:   0,
            autoSkip:      true,
            maxTicksLimit: 12,
          },
        },
      },
    }}
  />;
}

// ── Chart Card ─────────────────────────────────────────────────────────────────
function ChartCard({ ch, idx, onRemove }: { ch: any; idx: number; onRemove: () => void }) {
  const color = PALETTE[idx % PALETTE.length];
  const numericVals = Array.isArray(ch.values) && ch.values.length > 0 && typeof ch.values[0] === "number" ? ch.values as number[] : null;
  const maxVal = numericVals ? Math.max(...numericVals) : null;
  const minVal = numericVals ? Math.min(...numericVals) : null;
  const totalPts = Array.isArray(ch.values) ? ch.values.length : 0;
  const isPie = ch.type === "pie" || ch.type === "doughnut";
  const chartH = isPie ? 300 : 280;
  return (
    <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.07)", boxShadow: "0 4px 30px rgba(0,0,0,0.25)" }}>
      {/* Accent top bar */}
      <div className="h-[3px] w-full" style={{ background: `linear-gradient(90deg,${color},${color}44)` }} />
      <div className="flex items-start justify-between px-5 pt-4 pb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color, boxShadow: `0 0 5px ${color}` }} />
            <p className="text-[11px] font-black uppercase tracking-wide truncate" style={{ color: "var(--txt)" }}>{ch.title}</p>
            {ch.is_custom && <span className="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full" style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1", border: "1px solid rgba(99,102,241,0.25)" }}>Custom</span>}
          </div>
          {/* Axis context */}
          {ch.x_col && <p className="text-[9px] font-mono" style={{ color: "rgba(255,255,255,0.28)" }}>{ch.x_col}{ch.y_col ? ` → ${ch.y_col}` : ""}{ch.agg_type && ch.agg_type !== "none" ? ` · ${ch.agg_type}` : ""}</p>}
        </div>
        {ch.is_custom && (
          <button onClick={onRemove} className="ml-3 flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center transition-all" style={{ color: "rgba(255,255,255,0.25)" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#ef4444")} onMouseLeave={e => (e.currentTarget.style.color = "rgba(255,255,255,0.25)")}>
            <X size={12} />
          </button>
        )}
      </div>
      {/* Stats ribbon */}
      {numericVals && ch.type !== "boxplot" && (
        <div className="flex items-center gap-3 px-5 pb-2">
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.04)", color: "rgba(255,255,255,0.35)" }}>{totalPts} pts</span>
          {maxVal !== null && <span className="text-[9px] font-bold" style={{ color: "#10b981" }}>↑ {fmtNum(maxVal)}</span>}
          {minVal !== null && <span className="text-[9px] font-bold" style={{ color: "#f59e0b" }}>↓ {fmtNum(minVal)}</span>}
          {maxVal !== null && minVal !== null && maxVal !== minVal && <span className="text-[9px] font-bold" style={{ color: "rgba(255,255,255,0.3)" }}>Δ {fmtNum(maxVal - minVal)}</span>}
        </div>
      )}
      {/* Chart area — white container for maximum clarity of black axis labels */}
      <div style={{ height: chartH, position: "relative", padding: "10px", background: "#ffffff", borderRadius: "12px", margin: "0 12px 12px", border: "1px solid #cbd5e1" }}>
        {ch.type === "boxplot"
          ? <BoxPlotViz data={ch.values} formatted={ch.formatted_values} xLabel={ch.x_col} yLabel={ch.y_col} />
          : renderChart(ch, idx)
        }
      </div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export function DashboardTab() {
  const { uploadId, profile } = useWorkspace();
  const [isDashLoading,     setIsDashLoading]     = useState(false);
  const [dashStats,         setDashStats]          = useState<any[]>([]);
  const [dashCharts,        setDashCharts]         = useState<any[]>([]);
  const [dashSummary,       setDashSummary]        = useState("");
  const [dashIdStats,       setDashIdStats]        = useState<any>(null);
  const [dashNumericCols,   setDashNumericCols]    = useState<string[]>([]);
  const [dashInsights,      setDashInsights]       = useState<any[]>([]);
  const [profileCols,       setProfileCols]        = useState<string[]>([]);
  const [builderOpen,       setBuilderOpen]        = useState(false);
  const [customChart,       setCustomChart]        = useState({ id: null as any, chart_type: "bar", x_col: "", y_col: "", agg_type: "mean", title: "", is_area: false, top_n: 10 });
  const [isGeneratingChart, setIsGeneratingChart]  = useState(false);
  const [customChartError,  setCustomChartError]   = useState("");

  const loadDashboard = useCallback(async () => {
    if (!uploadId) return;
    setIsDashLoading(true);
    try {
      const res = await apiFetch("/dashboard/stats", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chart_dim: "", chart_metric: "", upload_id: uploadId }) });
      if (res.ok) {
        const d = await res.json();
        setDashStats(d.stats || []);
        setDashCharts(d.charts || []);
        setDashSummary(d.summary || "");
        setDashIdStats(d.id_stats || null);
        setDashNumericCols(d.numeric_cols || []);
        setDashInsights(d.insights || []);
        setProfileCols(d.cat_cols ? [...(d.cat_cols || []), ...(d.numeric_cols || [])] : profile?.columns?.map((c: any) => c.name) || []);
      }
    } catch (e) { console.error(e); }
    finally { setIsDashLoading(false); }
  }, [uploadId, profile]);

useEffect(() => { if (uploadId) loadDashboard(); }, [uploadId, loadDashboard]);

  const saveCustomChart = async () => {
    setCustomChartError(""); setIsGeneratingChart(true);
    try {
      const payload: any = {
        ...customChart,
        upload_id: uploadId,
        x_col: customChart.x_col ? customChart.x_col.trim() : "",
        y_col: customChart.y_col ? customChart.y_col.trim() : undefined,
      };
      if (!payload.y_col) delete payload.y_col;
      if (!payload.id) delete payload.id;
      if (!payload.title) delete payload.title;

      const res = await apiFetch("/dashboard/custom-chart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const d = await res.json().catch(() => ({}));
      if (!res.ok || d.error || d.detail) {
        let err = d.error || d.detail;
        if (Array.isArray(err)) err = err.map((e: any) => e.msg || e.detail || String(e)).join(", ");
        setCustomChartError(typeof err === "string" ? err : "Failed to generate chart");
        return;
      }
      setCustomChart({ id: null, chart_type: "bar", x_col: "", y_col: "", agg_type: "mean", title: "", is_area: false, top_n: 10 });
      setBuilderOpen(false);
      await loadDashboard();
    } catch (e: any) {
      setCustomChartError("Network error: " + (e.message || String(e)));
    } finally {
      setIsGeneratingChart(false);
    }
  };

  const removeChart = async (ch: any) => {
    if (!ch.is_custom) return;
    try {
      const res = await apiFetch("/dashboard/custom-chart/delete", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ upload_id: uploadId, chart_id: ch.id }) });
      if (res.ok) setDashCharts(prev => prev.filter(c => c.id !== ch.id));
    } catch (e) { console.error(e); }
  };

  const sel: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: "0.6rem", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "var(--txt)", fontSize: "11px", fontWeight: 600, width: "100%", outline: "none" };

  // Empty
  if (!dashStats.length && !isDashLoading) return (
    <div className="tab-panel px-4 py-6 md:px-6">
      <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Analytics Dashboard</h2>
          <p className="text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>KPIs · Trend Charts · Category Analysis · Distribution</p>
        </div>
        <button onClick={loadDashboard} className="bp flex items-center gap-2"><BarChart4 size={14} /> Generate Dashboard</button>
      </div>
      <div className="flex flex-col items-center justify-center gap-6 py-24 text-center">
        <div className="w-24 h-24 rounded-full flex items-center justify-center" style={{ background: "linear-gradient(135deg,rgba(99,102,241,0.15),rgba(99,102,241,0.04))", border: "1px solid rgba(99,102,241,0.2)" }}>
          <BarChart4 size={40} style={{ color: "#6366f1" }} />
        </div>
        <div>
          <p className="font-black text-base mb-1" style={{ color: "var(--txt)" }}>No Dashboard Yet</p>
          <p className="text-sm max-w-sm" style={{ color: "var(--txt-m)" }}>Click <strong>Generate Dashboard</strong> to automatically build KPI metrics, trend charts, and distribution analysis from your dataset.</p>
        </div>
        <button onClick={loadDashboard} className="px-6 py-3 rounded-xl font-bold text-sm text-white" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>Generate Dashboard</button>
      </div>
    </div>
  );

  // Skeleton
  if (isDashLoading && dashStats.length === 0) return (
    <div className="tab-panel px-4 py-6 md:px-6 space-y-6 animate-pulse">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <div key={i} className="rounded-2xl p-5 h-28" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.05)" }}><div className="h-2 w-16 rounded mb-4" style={{ background: "rgba(255,255,255,0.07)" }} /><div className="h-8 w-20 rounded" style={{ background: "rgba(255,255,255,0.1)" }} /></div>)}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
        {Array.from({ length: 6 }).map((_, i) => <div key={i} className="rounded-2xl p-5 h-72" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.05)" }}><div className="h-3 w-32 rounded mb-6" style={{ background: "rgba(255,255,255,0.07)" }} /><div className="h-44 w-full rounded-xl" style={{ background: "rgba(255,255,255,0.04)" }} /></div>)}
      </div>
    </div>
  );

  return (
    <div className="tab-panel space-y-6 px-4 py-4 md:px-6 md:py-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>Analytics Dashboard</h2>
          <p className="text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>{dashCharts.length} chart{dashCharts.length !== 1 ? "s" : ""} · {dashStats.length} KPIs · Live dataset analysis</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setBuilderOpen(b => !b)} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold border transition-all"
            style={{ borderColor: builderOpen ? "#6366f1" : "rgba(255,255,255,0.1)", background: builderOpen ? "rgba(99,102,241,0.1)" : "transparent", color: builderOpen ? "#6366f1" : "var(--txt-m)" }}>
            <Plus size={12} /> Add Chart
          </button>
          <button onClick={loadDashboard} disabled={isDashLoading} className="bp flex items-center gap-1.5">
            {isDashLoading ? <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg> : <RefreshCw size={13} />}
            {isDashLoading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      {dashStats.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {dashStats.map((stat, i) => <KpiCard key={stat.label} stat={stat} idx={i} />)}
        </div>
      )}

      {/* AI Summary */}
      {dashSummary && (
        <div className="rounded-2xl p-5 flex gap-4" style={{ background: "linear-gradient(135deg,rgba(99,102,241,0.07),rgba(139,92,246,0.03))", border: "1px solid rgba(99,102,241,0.18)" }}>
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}>
            <Activity size={15} className="text-white" />
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: "#6366f1" }}>AI Insight Summary</p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>{dashSummary}</p>
          </div>
        </div>
      )}

      {/* ID Stats */}
      {dashIdStats && (
        <div className="rounded-2xl p-5 flex items-center gap-6" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.07)" }}>
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "rgba(245,158,11,0.1)" }}>
            <GitBranch size={16} style={{ color: "#f59e0b" }} />
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: "var(--txt-m)" }}>Index Column — <span className="font-mono">{dashIdStats.col}</span></p>
            <div className="flex gap-6">
              {([["Unique", dashIdStats.total], ["Min", dashIdStats.min], ["Max", dashIdStats.max]] as [string,any][]).map(([l, v]) => (
                <div key={l}><p className="text-[9px] uppercase tracking-wider" style={{ color: "rgba(255,255,255,0.3)" }}>{l}</p><p className="text-lg font-black" style={{ color: "#f59e0b" }}>{v}</p></div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Chart Builder */}
      {builderOpen && (
        <div className="rounded-2xl overflow-hidden" style={{ background: "var(--surface)", border: "1px solid rgba(99,102,241,0.22)", boxShadow: "0 0 40px rgba(99,102,241,0.07)" }}>
          <div className="flex items-center gap-3 px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.07)", background: "rgba(99,102,241,0.05)" }}>
            <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}><BarChart4 size={14} className="text-white" /></div>
            <div><p className="text-sm font-black uppercase tracking-wide" style={{ color: "var(--txt)" }}>Chart Builder</p><p className="text-[10px]" style={{ color: "var(--txt-m)" }}>Create a custom visualization and pin it to your dashboard</p></div>
          </div>
          <div className="p-5 space-y-5">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest mb-2" style={{ color: "var(--txt-m)" }}>Chart Type</p>
              <div className="flex flex-wrap gap-2">
                {CHART_TYPES.map(ct => (
                  <button key={ct.id} onClick={() => setCustomChart(c => ({ ...c, chart_type: ct.id }))}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all"
                    style={customChart.chart_type === ct.id
                      ? { background: "#6366f1", color: "#fff", boxShadow: "0 0 12px rgba(99,102,241,0.35)" }
                      : { background: "rgba(255,255,255,0.05)", color: "var(--txt-m)", border: "1px solid rgba(255,255,255,0.08)" }
                    }>{ct.label}</button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>X Axis / Category</label>
                <select value={customChart.x_col} onChange={e => setCustomChart(c => ({ ...c, x_col: e.target.value }))} style={sel}>
                  <option value="">— Select Column —</option>
                  {profileCols.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              {!["histogram","boxplot"].includes(customChart.chart_type) && (
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Y Axis / Value</label>
                  <select value={customChart.y_col} onChange={e => setCustomChart(c => ({ ...c, y_col: e.target.value }))} style={sel}>
                    <option value="">— Count Rows —</option>
                    {dashNumericCols.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              )}
              {!["histogram","boxplot","scatter"].includes(customChart.chart_type) && (
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Aggregation</label>
                  <select value={customChart.agg_type} onChange={e => setCustomChart(c => ({ ...c, agg_type: e.target.value }))} style={sel}>
                    <option value="mean">Average (Mean)</option>
                    <option value="sum">Sum Total</option>
                    <option value="count">Count of Values</option>
                    <option value="none">None — Raw Rows</option>
                  </select>
                </div>
              )}
              {(customChart.chart_type === "pie" || customChart.chart_type === "doughnut") && (
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Max Slices</label>
                  <select value={customChart.top_n} onChange={e => setCustomChart(c => ({ ...c, top_n: parseInt(e.target.value) }))} style={sel}>
                    <option value={5}>Top 5</option><option value={10}>Top 10</option><option value={20}>Top 20</option><option value={500}>All</option>
                  </select>
                </div>
              )}
            </div>
            <div className="flex gap-3 items-end flex-wrap">
              <div className="flex-1 space-y-1.5 min-w-[180px]">
                <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Chart Title (optional)</label>
                <input type="text" value={customChart.title} onChange={e => setCustomChart(c => ({ ...c, title: e.target.value }))} placeholder="Auto-generated if blank" style={{ ...sel, fontFamily: "inherit" }} />
              </div>
              <button onClick={saveCustomChart} disabled={isGeneratingChart || !customChart.x_col}
                className="px-5 py-2 rounded-xl font-bold text-sm text-white transition-all"
                style={!customChart.x_col || isGeneratingChart ? { background: "rgba(99,102,241,0.3)", cursor: "not-allowed" } : { background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.25)" }}>
                {isGeneratingChart ? "Saving…" : "Add to Dashboard"}
              </button>
            </div>
            {customChartError && <p className="text-[11px] font-medium text-red-400">{customChartError}</p>}
          </div>
        </div>
      )}

      {/* Time Series & Advanced Forecast Section */}
      {dashInsights.filter((ins: any) => ins.type === "forecast").map((ins: any, i: number) => (
        <div key={`dash-fc-${i}`} className="w-full">
          <ForecastCard ins={ins} />
        </div>
      ))}

      {/* Charts Grid */}
      {dashCharts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {dashCharts.map((ch, i) => <ChartCard key={ch.id || `c-${i}`} ch={ch} idx={i} onRemove={() => removeChart(ch)} />)}
        </div>
      )}
    </div>
  );
}
