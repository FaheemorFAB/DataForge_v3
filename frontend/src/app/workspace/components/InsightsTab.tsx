"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement,
  LineElement, BarElement, ArcElement,
  Title, Tooltip, Legend, Filler,
} from "chart.js";
import { Scatter, Line, Bar, Doughnut } from "react-chartjs-2";
import { Sparkles, Brain, TrendingUp, TrendingDown, AlertTriangle, Activity, BarChart2, GitBranch, Layers, Zap, Target, ChevronDown } from "lucide-react";

ChartJS.register(
  CategoryScale, LinearScale, PointElement,
  LineElement, BarElement, ArcElement,
  Title, Tooltip, Legend, Filler
);

// ── Per-type colour palette ──────────────────────────────────────────────────
const TYPE_THEME: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  trend:              { bg: "rgba(99,102,241,0.12)",  border: "rgba(99,102,241,0.3)",  text: "#6366f1", glow: "#6366f1" },
  ranking:            { bg: "rgba(16,185,129,0.12)",  border: "rgba(16,185,129,0.3)",  text: "#10b981", glow: "#10b981" },
  correlation:        { bg: "rgba(245,158,11,0.12)",  border: "rgba(245,158,11,0.3)",  text: "#f59e0b", glow: "#f59e0b" },
  anomaly:            { bg: "rgba(239,68,68,0.12)",   border: "rgba(239,68,68,0.3)",   text: "#ef4444", glow: "#ef4444" },
  distribution:       { bg: "rgba(59,130,246,0.12)",  border: "rgba(59,130,246,0.3)",  text: "#3b82f6", glow: "#3b82f6" },
  contribution:       { bg: "rgba(20,184,166,0.12)",  border: "rgba(20,184,166,0.3)",  text: "#14b8a6", glow: "#14b8a6" },
  segment:            { bg: "rgba(139,92,246,0.12)",  border: "rgba(139,92,246,0.3)",  text: "#8b5cf6", glow: "#8b5cf6" },
  change:             { bg: "rgba(236,72,153,0.12)",  border: "rgba(236,72,153,0.3)",  text: "#ec4899", glow: "#ec4899" },
  data_quality:       { bg: "rgba(34,197,94,0.12)",   border: "rgba(34,197,94,0.3)",   text: "#22c55e", glow: "#22c55e" },
  feature_importance: { bg: "rgba(251,146,60,0.12)",  border: "rgba(251,146,60,0.3)",  text: "#fb923c", glow: "#fb923c" },
  outlier_summary:    { bg: "rgba(239,68,68,0.10)",   border: "rgba(239,68,68,0.25)",  text: "#f87171", glow: "#f87171" },
  numeric_summary:    { bg: "rgba(99,102,241,0.10)",  border: "rgba(99,102,241,0.25)", text: "#a78bfa", glow: "#a78bfa" },
  categorical:        { bg: "rgba(20,184,166,0.10)",  border: "rgba(20,184,166,0.25)", text: "#14b8a6", glow: "#14b8a6" },
  profile:            { bg: "rgba(255,255,255,0.04)", border: "rgba(255,255,255,0.1)", text: "rgba(255,255,255,0.5)", glow: "transparent" },
  forecast:           { bg: "rgba(0,212,255,0.10)",   border: "rgba(0,212,255,0.3)",   text: "#00d4ff", glow: "#00d4ff" },
};

const PIE_PALETTE = [
  "#6366f1","#10b981","#f59e0b","#ef4444","#8b5cf6",
  "#06b6d4","#ec4899","#f97316","#84cc16","#14b8a6",
];

function fmtN(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000)     return `${(v / 1_000).toFixed(1)}K`;
  return v % 1 === 0 ? String(v) : v.toFixed(2);
}

function toLabel(s: string): string {
  return (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function theme(type: string) {
  return TYPE_THEME[type] || TYPE_THEME.profile;
}

// ── Tooltip config ───────────────────────────────────────────────────────────
function mkTooltip(color: string) {
  return {
    displayColors: false,
    backgroundColor: "rgba(8,8,20,0.97)",
    borderColor: color,
    borderWidth: 1,
    titleColor: "rgba(255,255,255,0.95)",
    bodyColor: "rgba(255,255,255,0.7)",
    padding: 10,
    cornerRadius: 8,
    callbacks: {
      label: (ctx: any) => {
        const v = ctx.parsed?.y ?? ctx.parsed ?? ctx.raw;
        if (typeof v === "number") return `  ${fmtN(v)}`;
        if (v && typeof v.y === "number") return `  ${fmtN(v.y)}`;
        return `  ${v}`;
      },
    },
  };
}

// ── Base chart options ────────────────────────────────────────────────────────
function baseOpts(color: string, xLabel = "", yLabel = "", horizontal = false): any {
  const scaleBase = {
    ticks: { color: "#1e293b", font: { size: 11, weight: "bold" as const }, maxTicksLimit: 8 },
    grid: { color: "rgba(0,0,0,0.06)" },
    border: { color: "#94a3b8" },
  };
  return {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: horizontal ? ("y" as const) : ("x" as const),
    animation: { duration: 500 },
    layout: { padding: { top: 4, right: 8, bottom: 4, left: 4 } },
    plugins: { legend: { display: false }, tooltip: mkTooltip(color) },
    scales: {
      x: {
        ...scaleBase,
        title: {
          display: true,
          text: xLabel || "Category",
          color: "#0f172a",
          font: { size: 12, weight: "bold" as const },
          padding: { top: 4 },
        },
        ticks: {
          ...scaleBase.ticks,
          callback: horizontal ? (v: any) => fmtN(Number(v)) : undefined,
        },
      },
      y: {
        ...scaleBase,
        title: {
          display: true,
          text: yLabel || "Value",
          color: "#0f172a",
          font: { size: 12, weight: "bold" as const },
          padding: { bottom: 4 },
        },
        ticks: {
          ...scaleBase.ticks,
          callback: horizontal ? undefined : (v: any) => fmtN(Number(v)),
          maxTicksLimit: 6,
        },
        beginAtZero: !horizontal,
      },
    },
  };
}


// ── Safe chart_data parser helper ──────────────────────────────────────────────
function getChartData(ins: any): { labels: string[]; values: number[]; [key: string]: any } | null {
  if (!ins || !ins.chart_data) return null;
  let cd = ins.chart_data;
  if (typeof cd === "string") {
    try { cd = JSON.parse(cd); } catch { return null; }
  }
  if (!cd || typeof cd !== "object") return null;
  
  let labels = cd.labels;
  let values = cd.values;
  if (typeof labels === "string") { try { labels = JSON.parse(labels); } catch {} }
  if (typeof values === "string") { try { values = JSON.parse(values); } catch {} }
  
  if (!Array.isArray(labels) || !Array.isArray(values) || labels.length === 0 || values.length === 0) {
    return null;
  }
  return { ...cd, labels, values };
}

// ── 9 Dedicated chart renderers ───────────────────────────────────────────────
function renderInsightChart(ins: any): React.ReactNode {
  const cd   = getChartData(ins);
  const type = ins.type as string;
  const t    = theme(type);
  const col  = t.text;

  if (!cd) return null;

  const labels: string[] = cd.labels;
  const values: number[] = cd.values;
  const xLabel = toLabel(cd.x_label || "");
  const yLabel = toLabel(cd.y_label || ins.metric || "Value");

  // 1. TREND → smooth line with gradient fill
  if (type === "trend") {
    return (
      <Line
        data={{
          labels,
          datasets: [{
            label: yLabel, data: values,
            borderColor: col, backgroundColor: `${col}18`,
            borderWidth: 2.5, fill: true, tension: 0.4,
            pointRadius: 3, pointBackgroundColor: "#fff",
            pointBorderColor: col, pointBorderWidth: 2, pointHoverRadius: 6,
          }],
        }}
        options={baseOpts(col, xLabel, yLabel)}
      />
    );
  }

  // 2. RANKING / TOP_PERFORMER → horizontal bar ranked
  if (type === "ranking" || type === "top_performer") {
    const sortIdx = values.map((v, i) => [v, i] as [number, number]).sort((a, b) => b[0] - a[0]);
    const sLabels = sortIdx.map(([, i]) => labels[i]);
    const sValues = sortIdx.map(([v]) => v);
    return (
      <Bar
        data={{
          labels: sLabels,
          datasets: [{
            label: yLabel, data: sValues,
            backgroundColor: sLabels.map((_, i) => `${PIE_PALETTE[i % PIE_PALETTE.length]}cc`),
            borderColor:     sLabels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
            borderWidth: 1.5, borderRadius: 5, borderSkipped: false as const,
          }],
        }}
        options={baseOpts(col, yLabel, xLabel, true)}
      />
    );
  }

  // 3. CORRELATION → scatter plot
  if (type === "correlation") {
    const pts = labels.map((x: any, i: number) => ({ x: parseFloat(String(x)) || i, y: values[i] }));
    return (
      <Scatter
        data={{ datasets: [{ label: yLabel, data: pts, backgroundColor: `${col}99`, pointRadius: 5, pointHoverRadius: 8, pointBorderColor: col, pointBorderWidth: 1 }] }}
        options={{ ...baseOpts(col, toLabel(cd.col_x || "X"), toLabel(cd.col_y || "Y")), scales: { ...baseOpts(col).scales, x: { ...baseOpts(col).scales.x, type: "linear" as const } } }}
      />
    );
  }

  // 4. ANOMALY → bar with danger colours for outliers
  if (type === "anomaly") {
    const mean = cd.mean ?? 0;
    const hiThresh = cd.threshold_hi ?? null;
    return (
      <Bar
        data={{
          labels,
          datasets: [{
            label: yLabel, data: values,
            backgroundColor: values.map(v =>
              hiThresh !== null && (v > cd.threshold_hi || v < cd.threshold_lo)
                ? "rgba(239,68,68,0.8)"
                : "rgba(239,68,68,0.25)"
            ),
            borderColor: values.map(v =>
              hiThresh !== null && (v > cd.threshold_hi || v < cd.threshold_lo)
                ? "#ef4444" : "rgba(239,68,68,0.4)"
            ),
            borderWidth: 1.5, borderRadius: 4, borderSkipped: false as const,
          }],
        }}
        options={{
          ...baseOpts(col, xLabel || "Row", yLabel),
          plugins: {
            ...baseOpts(col).plugins,
            annotation: undefined,
          },
        }}
      />
    );
  }

  // 5. DISTRIBUTION → histogram bars (smooth colour gradient)
  if (type === "distribution") {
    return (
      <Bar
        data={{
          labels,
          datasets: [{
            label: yLabel, data: values,
            backgroundColor: labels.map((_, i) => `${col}${Math.round(55 + (i / labels.length) * 150).toString(16).padStart(2, "0")}`),
            borderColor: col, borderWidth: 1, borderRadius: 3,
          }],
        }}
        options={baseOpts(col, xLabel || "Range", yLabel || "Frequency")}
      />
    );
  }

  // 6. CONTRIBUTION → donut chart
  if (type === "contribution") {
    const total = values.reduce((s, v) => s + Math.abs(v), 0);
    return (
      <Doughnut
        data={{ labels, datasets: [{ data: values, backgroundColor: PIE_PALETTE, borderColor: "rgba(0,0,0,0.3)", borderWidth: 2, hoverOffset: 10 }] }}
        options={{
          responsive: true, maintainAspectRatio: false,
          animation: { duration: 500 },
          layout: { padding: 8 },
          plugins: {
            legend: { display: true, position: "right" as const, labels: { color: "#1e293b", font: { size: 11, weight: "bold" }, boxWidth: 12, padding: 12,
              generateLabels: (chart: any) => {
                const ds = chart.data.datasets[0];
                return (chart.data.labels || []).map((lbl: string, i: number) => {
                  const val = Number(ds.data[i]);
                  const pct = total > 0 ? ((Math.abs(val) / total) * 100).toFixed(1) : "0";
                  return { text: `${lbl} (${pct}%)`, fillStyle: PIE_PALETTE[i % PIE_PALETTE.length], strokeStyle: "rgba(0,0,0,0.3)", lineWidth: 1, index: i, hidden: false };
                });
              },
            }},
            tooltip: { ...mkTooltip(col), callbacks: { label: (ctx: any) => `  ${ctx.label}: ${fmtN(Number(ctx.parsed))} (${total > 0 ? ((Math.abs(Number(ctx.parsed)) / total) * 100).toFixed(1) : 0}%)` } },
          },
        }}
      />
    );
  }

  // 7. CATEGORICAL → donut chart
  if (type === "categorical") {
    const total = values.reduce((s, v) => s + Math.abs(v), 0);
    return (
      <Doughnut
        data={{ labels, datasets: [{ data: values, backgroundColor: PIE_PALETTE.map(c => `${c}cc`), borderColor: "rgba(0,0,0,0.3)", borderWidth: 2, hoverOffset: 10 }] }}
        options={{
          responsive: true, maintainAspectRatio: false, animation: { duration: 500 }, layout: { padding: 8 },
          plugins: {
            legend: { display: true, position: "right" as const, labels: { color: "#1e293b", font: { size: 11, weight: "bold" }, boxWidth: 12, padding: 12 } },
            tooltip: { ...mkTooltip(col), callbacks: { label: (ctx: any) => `  ${ctx.label}: ${fmtN(Number(ctx.parsed))} (${total > 0 ? ((Math.abs(Number(ctx.parsed)) / total) * 100).toFixed(1) : 0}%)` } },
          },
        }}
      />
    );
  }

  // 8. SEGMENT → horizontal grouped bar
  if (type === "segment") {
    return (
      <Bar
        data={{
          labels,
          datasets: [{
            label: yLabel, data: values,
            backgroundColor: labels.map((_, i) => `${PIE_PALETTE[i % PIE_PALETTE.length]}bb`),
            borderColor:     labels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
            borderWidth: 1.5, borderRadius: 5, borderSkipped: false as const,
          }],
        }}
        options={baseOpts(col, yLabel, xLabel, true)}
      />
    );
  }

  // 9. CHANGE → before/after 2-bar chart with colour coding
  if (type === "change") {
    const changePct = cd.change_pct ?? 0;
    const isUp = changePct >= 0;
    return (
      <Bar
        data={{
          labels,
          datasets: [{
            label: yLabel, data: values,
            backgroundColor: ["rgba(99,102,241,0.6)", isUp ? "rgba(16,185,129,0.7)" : "rgba(239,68,68,0.7)"],
            borderColor:     ["#6366f1", isUp ? "#10b981" : "#ef4444"],
            borderWidth: 2, borderRadius: 8, borderSkipped: false as const,
          }],
        }}
        options={baseOpts(col, xLabel || "Period", yLabel)}
      />
    );
  }

  // 10. FORECAST → handled by ForecastCard; return null here (InsightCard switches)
  if (type === "forecast") return null;

  // 10. DATA QUALITY → horizontal completion bars
  if (type === "data_quality") {
    return (
      <Bar
        data={{
          labels,
          datasets: [{
            label: "Missing %", data: values,
            backgroundColor: values.map(v => v > 20 ? "rgba(239,68,68,0.7)" : v > 5 ? "rgba(245,158,11,0.7)" : "rgba(34,197,94,0.7)"),
            borderColor:     values.map(v => v > 20 ? "#ef4444" : v > 5 ? "#f59e0b" : "#22c55e"),
            borderWidth: 1.5, borderRadius: 4, borderSkipped: false as const,
          }],
        }}
        options={baseOpts(col, "Missing %", "Column", true)}
      />
    );
  }

  // 11. FEATURE_IMPORTANCE → ranked horizontal bar
  if (type === "feature_importance") {
    const sortIdx = values.map((v, i) => [v, i] as [number, number]).sort((a, b) => b[0] - a[0]);
    const sLabels = sortIdx.map(([, i]) => labels[i]);
    const sValues = sortIdx.map(([v]) => v);
    return (
      <Bar
        data={{
          labels: sLabels,
          datasets: [{
            label: "Importance", data: sValues,
            backgroundColor: sLabels.map((_, i) => `${PIE_PALETTE[i % PIE_PALETTE.length]}cc`),
            borderColor:     sLabels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
            borderWidth: 1.5, borderRadius: 5, borderSkipped: false as const,
          }],
        }}
        options={baseOpts(col, "Importance Score", "Feature", true)}
      />
    );
  }

  // 12. OUTLIER_SUMMARY → bar with danger threshold
  if (type === "outlier_summary") {
    return (
      <Bar
        data={{
          labels,
          datasets: [{
            label: "Outlier Count", data: values,
            backgroundColor: values.map(v => v > 0 ? "rgba(239,68,68,0.65)" : "rgba(34,197,94,0.4)"),
            borderColor:     values.map(v => v > 0 ? "#ef4444" : "#22c55e"),
            borderWidth: 1.5, borderRadius: 4, borderSkipped: false as const,
          }],
        }}
        options={baseOpts(col, "Outlier Count", "Column", true)}
      />
    );
  }

  // 13. NUMERIC_SUMMARY / fallback → horizontal bar
  return (
    <Bar
      data={{
        labels,
        datasets: [{
          label: yLabel, data: values,
          backgroundColor: labels.map((_, i) => `${PIE_PALETTE[i % PIE_PALETTE.length]}bb`),
          borderColor:     labels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
          borderWidth: 1.5, borderRadius: 5, borderSkipped: false as const,
        }],
      }}
      options={baseOpts(col, yLabel, "Column", true)}
    />
  );
}

// ── Forecast Card — Full interactive predictive analytics card ────────────────
export function ForecastCard({ ins }: { ins: any }) {
  const [activeTab, setActiveTab] = useState<"forecast" | "decomp" | "models">("forecast");
  const [horizon, setHorizon] = useState<number | null>(null);
  const [runningForecast, setRunningForecast] = useState(false);
  const [localData, setLocalData] = useState<any>(null);
  const { uploadId } = useWorkspace();

  const cd = localData ?? (ins.chart_data && typeof ins.chart_data === "string" ? JSON.parse(ins.chart_data) : ins.chart_data);
  const stats   = cd?.summary_stats || {};
  const mapes   = cd?.model_mapes   || {};
  const decomp  = cd?.decomposition;
  const col     = "#00d4ff";

  const histLabels  = cd?.labels          || [];
  const histValues  = cd?.values          || [];
  const fcLabels    = cd?.forecast_labels || [];
  const fcValues    = cd?.forecast_values || [];
  const upper95     = cd?.upper_95        || [];
  const lower95     = cd?.lower_95        || [];
  const upper80     = cd?.upper_80        || [];
  const lower80     = cd?.lower_80        || [];

  const allLabels = [...histLabels, ...fcLabels];
  const n_hist    = histLabels.length;
  const n_fc      = fcLabels.length;

  // Re-run forecast with custom horizon
  const rerunForecast = useCallback(async (h: number) => {
    if (!uploadId) return;
    setRunningForecast(true);
    try {
      const res = await apiFetch("/insights/forecast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          upload_id: uploadId,
          metric_col: ins.metric,
          horizon: h,
          include_decomposition: true,
        }),
      });
      if (res.ok) {
        const d = await res.json();
        setLocalData({
          labels:           d.historical_labels || [],
          values:           d.historical_values || [],
          forecast_labels:  d.forecast_labels   || [],
          forecast_values:  d.forecast_values   || [],
          upper_95:         d.upper_95          || [],
          lower_95:         d.lower_95          || [],
          upper_80:         d.upper_80          || [],
          lower_80:         d.lower_80          || [],
          decomposition:    d.decomposition,
          freq:             d.freq,
          horizon:          d.horizon,
          model_mapes:      d.model_mapes       || {},
          best_model:       d.best_model,
          summary_stats:    d.summary_stats     || {},
        });
      }
    } catch (e) { console.error(e); }
    finally { setRunningForecast(false); }
  }, [uploadId, ins.metric]);

  const growthPct  = stats.projected_growth_pct ?? 0;
  const isPositive = growthPct >= 0;
  const bestModel  = cd?.best_model || "Ensemble";
  const mapeValues = Object.values(mapes as Record<string, number>);
  const avgMAPE    = mapeValues.length > 0
    ? (mapeValues.reduce((a, b) => a + b, 0) / mapeValues.length).toFixed(1)
    : String(stats.avg_mape ?? "—");

  const HORIZONS = [
    { label: "7d",   v: 7 },
    { label: "30d",  v: 30 },
    { label: "90d",  v: 90 },
    { label: "1yr",  v: 365 },
  ];

  const chartData = {
    labels: allLabels,
    datasets: [
      {
        label: "Upper 95%",
        data: [...Array(n_hist).fill(null), ...upper95],
        borderColor: "transparent",
        backgroundColor: "rgba(0,212,255,0.07)",
        fill: "+1" as const,
        pointRadius: 0,
        tension: 0.4,
        borderWidth: 0,
      },
      {
        label: "Lower 95%",
        data: [...Array(n_hist).fill(null), ...lower95],
        borderColor: "transparent",
        backgroundColor: "rgba(0,212,255,0.07)",
        fill: false as const,
        pointRadius: 0,
        tension: 0.4,
        borderWidth: 0,
      },
      {
        label: "Upper 80%",
        data: [...Array(n_hist).fill(null), ...upper80],
        borderColor: "transparent",
        backgroundColor: "rgba(0,212,255,0.11)",
        fill: "+1" as const,
        pointRadius: 0,
        tension: 0.4,
        borderWidth: 0,
      },
      {
        label: "Lower 80%",
        data: [...Array(n_hist).fill(null), ...lower80],
        borderColor: "transparent",
        backgroundColor: "rgba(0,212,255,0.11)",
        fill: false as const,
        pointRadius: 0,
        tension: 0.4,
        borderWidth: 0,
      },
      {
        label: "Historical",
        data: [...histValues, ...Array(n_fc).fill(null)],
        borderColor: "rgba(99,102,241,0.9)",
        backgroundColor: "rgba(99,102,241,0.08)",
        borderWidth: 2.5,
        fill: false as const,
        pointRadius: 2,
        pointBackgroundColor: "#6366f1",
        tension: 0.35,
      },
      {
        label: "Forecast",
        data: [...Array(n_hist).fill(null), ...fcValues],
        borderColor: "#00d4ff",
        backgroundColor: "rgba(0,212,255,0.12)",
        borderWidth: 2.5,
        borderDash: [6, 4],
        fill: false as const,
        pointRadius: 3,
        pointBackgroundColor: "#00d4ff",
        tension: 0.35,
      },
    ],
  };

  const chartOpts: any = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500 },
    layout: { padding: { top: 4, right: 8, bottom: 4, left: 4 } },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: "#000000",
          font: { size: 11, weight: "bold" },
          boxWidth: 12,
          filter: (item: any) => ["Historical", "Forecast"].includes(item.text),
        },
      },
      tooltip: {
        ...mkTooltip(col),
        filter: (item: any) => ["Historical", "Forecast"].includes(item.dataset.label),
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: "Date / Time",
          color: "#000000",
          font: { size: 12, weight: "bold" },
          padding: { top: 4 },
        },
        ticks: { color: "#000000", font: { size: 11, weight: "bold" }, maxTicksLimit: 8 },
        grid: { color: "rgba(0,0,0,0.08)" },
        border: { color: "#000000" },
      },
      y: {
        title: {
          display: true,
          text: toLabel(ins.metric || "Value"),
          color: "#000000",
          font: { size: 12, weight: "bold" },
          padding: { bottom: 4 },
        },
        ticks: { color: "#000000", font: { size: 11, weight: "bold" }, callback: (v: any) => fmtN(Number(v)) },
        grid: { color: "rgba(0,0,0,0.08)" },
        border: { color: "#000000" },
      },
    },
  };

  return (
    <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "var(--surface)", border: "1px solid rgba(0,212,255,0.28)", boxShadow: "0 4px 32px rgba(0,0,0,0.28), 0 0 40px rgba(0,212,255,0.05)", gridColumn: "1 / -1" }}>
      {/* Accent bar */}
      <div className="h-[3px] w-full" style={{ background: "linear-gradient(90deg,#6366f1,#00d4ff,#6366f1)" }} />

      {/* Header */}
      <div className="px-5 pt-5 pb-3 flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "linear-gradient(135deg,rgba(0,212,255,0.18),rgba(99,102,241,0.18))", border: "1px solid rgba(0,212,255,0.25)" }}>
            <GitBranch size={16} style={{ color: "#00d4ff" }} />
          </div>
          <div>
            <p className="font-black text-sm leading-tight" style={{ color: "var(--txt)" }}>{ins.title}</p>
            <p className="text-[10px] font-mono mt-0.5" style={{ color: "var(--txt-m)" }}>Predictive Analytics · {bestModel}</p>
          </div>
        </div>
        <span className="text-[9px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full" style={{ background: "rgba(0,212,255,0.1)", color: "#00d4ff", border: "1px solid rgba(0,212,255,0.25)" }}>
          forecast
        </span>
      </div>

      {/* Description */}
      <p className="px-5 pb-3 text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>{ins.description}</p>

      {/* KPI pills */}
      <div className="px-5 pb-4 flex flex-wrap gap-2">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl" style={{ background: isPositive ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)", border: `1px solid ${isPositive ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}` }}>
          {isPositive ? <TrendingUp size={11} style={{ color: "#10b981" }} /> : <TrendingDown size={11} style={{ color: "#ef4444" }} />}
          <span className="text-[10px] font-black" style={{ color: isPositive ? "#10b981" : "#ef4444" }}>{isPositive ? "+" : ""}{growthPct.toFixed(1)}% Projected</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl" style={{ background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)" }}>
          <Target size={11} style={{ color: "#00d4ff" }} />
          <span className="text-[10px] font-black" style={{ color: "#00d4ff" }}>Est. {fmtN(stats.proj_end_val ?? 0)}</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.2)" }}>
          <Zap size={11} style={{ color: "#f59e0b" }} />
          <span className="text-[10px] font-black" style={{ color: "#f59e0b" }}>MAPE {avgMAPE}%</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl" style={{ background: "rgba(139,92,246,0.08)", border: "1px solid rgba(139,92,246,0.2)" }}>
          <BarChart2 size={11} style={{ color: "#8b5cf6" }} />
          <span className="text-[10px] font-black" style={{ color: "#8b5cf6" }}>{stats.n_points ?? 0} pts</span>
        </div>
      </div>

      {/* Tab bar + Horizon selector */}
      <div className="px-5 pb-2 flex items-center justify-between flex-wrap gap-2">
        <div className="flex gap-1">
          {(["forecast", "decomp", "models"] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className="text-[10px] font-black uppercase tracking-wider px-3 py-1.5 rounded-lg transition-all"
              style={{ background: activeTab === tab ? "rgba(0,212,255,0.15)" : "transparent", color: activeTab === tab ? "#00d4ff" : "var(--txt-m)", border: `1px solid ${activeTab === tab ? "rgba(0,212,255,0.3)" : "transparent"}` }}>
              {tab === "forecast" ? "Forecast" : tab === "decomp" ? "Decompose" : "Models"}
            </button>
          ))}
        </div>
        {activeTab === "forecast" && (
          <div className="flex gap-1">
            {HORIZONS.map(h => (
              <button key={h.v}
                onClick={() => { setHorizon(h.v); rerunForecast(h.v); }}
                disabled={runningForecast}
                className="text-[9px] font-black px-2.5 py-1 rounded-lg transition-all"
                style={{
                  background: (horizon ?? cd?.horizon ?? 30) === h.v ? "rgba(0,212,255,0.2)" : "rgba(255,255,255,0.04)",
                  color: (horizon ?? cd?.horizon ?? 30) === h.v ? "#00d4ff" : "var(--txt-m)",
                  border: `1px solid ${(horizon ?? cd?.horizon ?? 30) === h.v ? "rgba(0,212,255,0.35)" : "var(--border)"}`,
                  opacity: runningForecast ? 0.5 : 1,
                }}>
                {runningForecast && (horizon ?? cd?.horizon ?? 30) === h.v ? "…" : h.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Chart area */}
      <div className="mx-3 mb-4 rounded-xl p-3 bg-white border border-slate-300 shadow-inner" style={{ height: 290, position: "relative" }}>
        {activeTab === "forecast" && (
          <>
            {runningForecast && (
              <div className="absolute inset-0 flex items-center justify-center z-10 rounded-xl" style={{ background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)" }}>
                <div className="flex flex-col items-center gap-2">
                  <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="#00d4ff" strokeWidth="4"/><path className="opacity-75" fill="#00d4ff" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                  <p className="text-[10px] font-black" style={{ color: "#00d4ff" }}>Running forecast…</p>
                </div>
              </div>
            )}
            <Line data={chartData} options={chartOpts} />
          </>
        )}

        {activeTab === "decomp" && decomp && (
          <Line
            data={{
              labels: decomp.labels,
              datasets: [
                { label: "Trend",    data: decomp.trend,    borderColor: "#6366f1",           backgroundColor: "transparent", borderWidth: 2,   pointRadius: 0, tension: 0.4 },
                { label: "Seasonal", data: decomp.seasonal, borderColor: "#10b981",            backgroundColor: "transparent", borderWidth: 1.5, pointRadius: 0, tension: 0.4, borderDash: [4, 3] },
                { label: "Residual", data: decomp.residual, borderColor: "rgba(239,68,68,0.6)", backgroundColor: "transparent", borderWidth: 1,   pointRadius: 0, tension: 0.3 },
              ],
            }}
            options={{ ...chartOpts, plugins: { ...chartOpts.plugins, legend: { display: true, labels: { color: "#1e293b", font: { size: 10, weight: "bold" }, boxWidth: 12 } } } }}
          />
        )}
        {activeTab === "decomp" && !decomp && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>Decomposition not available for this dataset length.</p>
          </div>
        )}

        {activeTab === "models" && (
          <div className="h-full overflow-auto flex flex-col gap-3 px-2 py-4">
            <p className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: "#1e293b" }}>Model Accuracy (MAPE — lower is better)</p>
            {Object.entries(mapes as Record<string, number>).map(([name, mape]) => {
              const isB = name === bestModel;
              const barW = Math.max(5, Math.min(100, 100 - mape));
              return (
                <div key={name} className="flex items-center gap-3">
                  <span className="text-[10px] font-bold flex-shrink-0" style={{ width: 120, color: isB ? "#00d4ff" : "#1e293b" }}>
                    {name}{isB ? " ★" : ""}
                  </span>
                  <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "rgba(0,0,0,0.08)" }}>
                    <div className="h-full rounded-full transition-all" style={{ width: `${barW}%`, background: isB ? "linear-gradient(90deg,#00d4ff,#6366f1)" : "rgba(0,0,0,0.25)" }} />
                  </div>
                  <span className="text-[10px] font-mono font-bold" style={{ width: 60, textAlign: "right", color: isB ? "#00d4ff" : "#1e293b" }}>{mape.toFixed(1)}% err</span>
                </div>
              );
            })}
            {Object.keys(mapes).length === 0 && (
              <p className="text-[11px]" style={{ color: "#1e293b" }}>No model metrics available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Insight Card ──────────────────────────────────────────────────────────────
function InsightCard({ ins, idx }: { ins: any; idx: number }) {
  // Forecast insights get their own dedicated card
  if (ins.type === "forecast") return <ForecastCard ins={ins} />;

  const t    = theme(ins.type);
  const imp  = Math.round((ins.importance ?? 0) * 100);
  const cd   = getChartData(ins);
  const hasChart = !!cd;

  return (
    <div className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "var(--surface)", border: `1px solid ${t.border}`, boxShadow: `0 4px 24px rgba(0,0,0,0.25), 0 0 0 1px ${t.border}` }}>
      {/* Colour accent bar */}
      <div className="h-[3px] w-full" style={{ background: `linear-gradient(90deg,${t.text},${t.text}44)` }} />

      {/* Header */}
      <div className="px-4 pt-4 pb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-black text-sm leading-tight truncate" style={{ color: "var(--txt)" }}>{ins.title}</p>
          {ins.metric && <p className="text-[9px] font-mono mt-0.5" style={{ color: "var(--txt-m)" }}>{ins.metric}</p>}
        </div>
        <span className="text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded-full flex-shrink-0 whitespace-nowrap" style={{ background: t.bg, color: t.text, border: `1px solid ${t.border}` }}>
          {ins.type?.replace(/_/g, " ")}
        </span>
      </div>

      {/* Description */}
      <p className="px-4 pb-2 text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>{ins.description}</p>

      {/* Importance bar */}
      <div className="px-4 pb-3 flex items-center gap-2">
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Importance</span>
        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--inp-bg)" }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${imp}%`, background: `linear-gradient(90deg,${t.text},${t.text}88)` }} />
        </div>
        <span className="font-mono text-[10px] font-bold" style={{ color: t.text }}>{imp}%</span>
      </div>

      {/* Chart */}
      {hasChart ? (
        <div className="mx-3 mb-4 rounded-xl p-3 bg-white border border-slate-300 shadow-inner" style={{ height: 230, position: "relative" }}>
          {renderInsightChart(ins)}
        </div>
      ) : ins.type === "profile" ? (
        <div className="mx-4 mb-4 rounded-xl p-3" style={{ background: "var(--inp-bg)", border: "1px solid var(--border)" }}>
          <p className="text-[10px] leading-relaxed" style={{ color: "var(--txt-m)" }}>No chart available for this insight type.</p>
        </div>
      ) : null}
    </div>
  );
}

// ── Main Tab ──────────────────────────────────────────────────────────────────
export function InsightsTab() {
  const { profile, uploadId } = useWorkspace();
  const [insightTopN,       setInsightTopN]       = useState("9");
  const [isRunning,         setIsRunning]          = useState(false);
  const [insightError,      setInsightError]       = useState("");
  const [insightCards,      setInsightCards]       = useState<any[]>([]);
  const [insightSummary,    setInsightSummary]     = useState("");
  const [insightSchema,     setInsightSchema]      = useState<any>(null);

  useEffect(() => {
    if (!uploadId) return;
    apiFetch(`/insights/current?upload_id=${uploadId}`)
      .then(res => res.ok ? res.json() : null)
      .then(d => {
        if (d && d.insights && Array.isArray(d.insights) && d.insights.length > 0) {
          setInsightCards(d.insights);
          setInsightSummary(d.summary || "");
          setInsightSchema(d.schema || null);
        }
      })
      .catch(console.error);
  }, [uploadId]);

  const runInsights = async () => {
    setIsRunning(true);
    setInsightError("");
    setInsightCards([]);
    setInsightSummary("");
    try {
      const res = await apiFetch("/insights/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ top_n: parseInt(insightTopN), use_gemini: false, upload_id: uploadId }),
      });

      if (!res.ok) {
        const text = await res.text();
        let msg = `HTTP ${res.status}`;
        try { const d = JSON.parse(text); msg = d.error || msg; } catch { msg = text.substring(0, 150) || msg; }
        setInsightError(msg);
        return;
      }

      const data = await res.json();
      if (data.error) { setInsightError(data.error); return; }

      if (data.sync || !data.task_id) {
        setInsightCards(data.insights || []);
        setInsightSummary(data.summary || "");
        setInsightSchema(data.schema || null);
        return;
      }

      // Polling fallback for async tasks
      const pollTask = async (taskId: string) => {
        for (let i = 0; i < 60; i++) {
          await new Promise(r => setTimeout(r, 2000));
          const pRes = await apiFetch(`/tasks/status/${taskId}`);
          if (!pRes.ok) throw new Error("Task check failed");
          const pData = await pRes.json();
          if (pData.status === "success" || pData.status === "completed") return;
          if (pData.status === "failure" || pData.status === "failed") throw new Error(pData.error || "Insight generation failed");
        }
        throw new Error("Timeout waiting for insights");
      };

      await pollTask(data.task_id);
      const cRes = await apiFetch(`/insights/current?upload_id=${uploadId}`);
      if (cRes.ok) {
        const cData = await cRes.json();
        setInsightCards(cData.insights || []);
        setInsightSummary(cData.summary || "");
        setInsightSchema(cData.schema || null);
      }
    } catch (e: any) {
      setInsightError(String(e.message || e));
    } finally {
      setIsRunning(false);
    }
  };

  // ── Empty state ─────────────────────────────────────────────────────────────
  if (!insightCards.length && !isRunning) return (
    <div className="tab-panel px-4 py-6 md:px-6">
      <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Insight Engine</h2>
          <p className="text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>Trends · Anomalies · Correlations · Rankings · Distributions · Contributions</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={insightTopN} onChange={e => setInsightTopN(e.target.value)} className="inp" style={{ width: "auto", padding: ".4rem .7rem", fontSize: ".75rem", fontWeight: 700 }}>
            <option value="3">3 insights</option>
            <option value="6">6 insights</option>
            <option value="9">9 insights</option>
          </select>
          <button onClick={runInsights} className="bp flex items-center gap-2"><Sparkles size={14} /> Run Insights</button>
        </div>
      </div>

      {insightError && (
        <div className="p-4 rounded-xl font-mono text-sm text-red-400 mb-6" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>{insightError}</div>
      )}

      <div className="flex flex-col items-center justify-center gap-6 py-24 text-center">
        <div className="w-24 h-24 rounded-full flex items-center justify-center" style={{ background: "linear-gradient(135deg,rgba(99,102,241,0.15),rgba(99,102,241,0.04))", border: "1px solid rgba(99,102,241,0.2)" }}>
          <Brain size={40} style={{ color: "#6366f1" }} />
        </div>
        <div>
          <p className="font-black text-base mb-1" style={{ color: "var(--txt)" }}>No Insights Yet</p>
          <p className="text-sm max-w-sm" style={{ color: "var(--txt-m)" }}>Click <strong>Run Insights</strong> to auto-detect trends, anomalies, top performers, correlations, distributions, and more — each with a dedicated visual.</p>
        </div>
        <button onClick={runInsights} className="px-6 py-3 rounded-xl font-bold text-sm text-white" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>Run Insights</button>
      </div>
    </div>
  );

  // ── Loading skeleton ─────────────────────────────────────────────────────────
  if (isRunning && !insightCards.length) return (
    <div className="tab-panel px-4 py-6 md:px-6 space-y-6 animate-pulse">
      <div className="h-8 w-48 rounded-xl" style={{ background: "rgba(255,255,255,0.07)" }} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="rounded-2xl p-5 h-72" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.05)" }}>
            <div className="h-3 w-32 rounded mb-4" style={{ background: "rgba(255,255,255,0.07)" }} />
            <div className="h-2 w-full rounded mb-2" style={{ background: "rgba(255,255,255,0.05)" }} />
            <div className="h-2 w-3/4 rounded mb-6" style={{ background: "rgba(255,255,255,0.04)" }} />
            <div className="h-36 w-full rounded-xl" style={{ background: "rgba(255,255,255,0.03)" }} />
          </div>
        ))}
      </div>
    </div>
  );

  // ── Results ──────────────────────────────────────────────────────────────────
  return (
    <div className="tab-panel space-y-6 px-4 py-4 md:px-6 md:py-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>Insight Engine</h2>
          <p className="text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>{insightCards.length} insight{insightCards.length !== 1 ? "s" : ""} generated · {insightSchema?.dataset_type || "general"} dataset</p>
        </div>
        <div className="flex items-center gap-2">
          <select value={insightTopN} onChange={e => setInsightTopN(e.target.value)} className="inp" style={{ width: "auto", padding: ".4rem .7rem", fontSize: ".75rem", fontWeight: 700 }}>
            <option value="3">3 insights</option>
            <option value="6">6 insights</option>
            <option value="9">9 insights</option>
          </select>
          <button onClick={runInsights} disabled={isRunning} className="bp flex items-center gap-1.5">
            {isRunning
              ? <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              : <Sparkles size={13} />
            }
            {isRunning ? "Analysing…" : "Re-run"}
          </button>
        </div>
      </div>

      {/* Schema pill row */}
      {insightSchema && (
        <div className="flex flex-wrap gap-2 items-center">
          {insightSchema.dataset_type && (
            <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-full" style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1", border: "1px solid rgba(99,102,241,0.25)" }}>
              {insightSchema.dataset_type}
            </span>
          )}
          {(insightSchema.metrics || []).slice(0, 4).map((m: string) => (
            <span key={m} className="text-[10px] font-mono px-2 py-0.5 rounded-full" style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.2)" }}>{m}</span>
          ))}
          {(insightSchema.dimensions || []).slice(0, 3).map((d: string) => (
            <span key={d} className="text-[10px] font-mono px-2 py-0.5 rounded-full" style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b", border: "1px solid rgba(245,158,11,0.2)" }}>{d}</span>
          ))}
        </div>
      )}

      {/* AI Summary */}
      {insightSummary && (
        <div className="rounded-2xl p-5 flex gap-4" style={{ background: "linear-gradient(135deg,rgba(99,102,241,0.07),rgba(139,92,246,0.03))", border: "1px solid rgba(99,102,241,0.18)" }}>
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)" }}>
            <Activity size={15} className="text-white" />
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: "#6366f1" }}>AI Summary</p>
            <p className="text-xs leading-relaxed whitespace-pre-line" style={{ color: "var(--txt-m)" }}>{insightSummary}</p>
          </div>
        </div>
      )}

      {insightError && (
        <div className="p-4 rounded-xl font-mono text-sm text-red-400" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>{insightError}</div>
      )}

      {/* Cards — forecast cards rendered full-width first, then regular grid */}
      {insightCards.filter(ins => ins.type === "forecast").map((ins, i) => (
        <InsightCard key={`fc-${i}`} ins={ins} idx={i} />
      ))}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {insightCards.filter(ins => ins.type !== "forecast").map((ins, i) => <InsightCard key={i} ins={ins} idx={i} />)}
      </div>
    </div>
  );
}
