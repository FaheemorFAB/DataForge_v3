"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, PointElement,
  LineElement, BarElement, ArcElement,
  Title, Tooltip, Legend, Filler,
} from "chart.js";
import { Scatter, Line, Bar, Doughnut } from "react-chartjs-2";
import { getChartThemeColors } from "@/lib/chartTheme";
import {
  Sparkles, Brain, TrendingUp, TrendingDown, AlertTriangle, Activity,
  BarChart2, GitBranch, Layers, Zap, Target, ChevronDown, Pin, Shield, Tag, X, Check,
  Copy, CheckCircle2, Users, FileText, LayoutDashboard
} from "lucide-react";

ChartJS.register(
  CategoryScale, LinearScale, PointElement,
  LineElement, BarElement, ArcElement,
  Title, Tooltip, Legend, Filler
);

// -- Per-type colour palette --
const TYPE_THEME: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  trend: { bg: "rgba(99,102,241,0.12)", border: "rgba(99,102,241,0.3)", text: "#6366f1", glow: "#6366f1" },
  ranking: { bg: "rgba(16,185,129,0.12)", border: "rgba(16,185,129,0.3)", text: "#10b981", glow: "#10b981" },
  correlation: { bg: "rgba(245,158,11,0.12)", border: "rgba(245,158,11,0.3)", text: "#f59e0b", glow: "#f59e0b" },
  anomaly: { bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.3)", text: "#ef4444", glow: "#ef4444" },
  distribution: { bg: "rgba(59,130,246,0.12)", border: "rgba(59,130,246,0.3)", text: "#3b82f6", glow: "#3b82f6" },
  contribution: { bg: "rgba(20,184,166,0.12)", border: "rgba(20,184,166,0.3)", text: "#14b8a6", glow: "#14b8a6" },
  segment: { bg: "rgba(139,92,246,0.12)", border: "rgba(139,92,246,0.3)", text: "#8b5cf6", glow: "#8b5cf6" },
  change: { bg: "rgba(236,72,153,0.12)", border: "rgba(236,72,153,0.3)", text: "#ec4899", glow: "#ec4899" },
  data_quality: { bg: "rgba(34,197,94,0.12)", border: "rgba(34,197,94,0.3)", text: "#22c55e", glow: "#22c55e" },
  feature_importance: { bg: "rgba(251,146,60,0.12)", border: "rgba(251,146,60,0.3)", text: "#fb923c", glow: "#fb923c" },
  outlier_summary: { bg: "rgba(239,68,68,0.10)", border: "rgba(239,68,68,0.25)", text: "#f87171", glow: "#f87171" },
  numeric_summary: { bg: "rgba(99,102,241,0.10)", border: "rgba(99,102,241,0.25)", text: "#a78bfa", glow: "#a78bfa" },
  categorical: { bg: "rgba(20,184,166,0.10)", border: "rgba(20,184,166,0.25)", text: "#14b8a6", glow: "#14b8a6" },
  profile: { bg: "rgba(255,255,255,0.04)", border: "rgba(255,255,255,0.1)", text: "rgba(255,255,255,0.5)", glow: "transparent" },
  forecast: { bg: "rgba(0,212,255,0.10)", border: "rgba(0,212,255,0.3)", text: "#00d4ff", glow: "#00d4ff" },
};

const PIE_PALETTE = [
  "#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#06b6d4", "#ec4899", "#f97316", "#84cc16", "#14b8a6",
];

function fmtN(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v % 1 === 0 ? String(v) : v.toFixed(2);
}

function toLabel(s: string): string {
  return (s || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function theme(type: string) {
  return TYPE_THEME[type] || TYPE_THEME.profile;
}

// -- Tooltip config --
function mkTooltip(color: string) {
  const tc = getChartThemeColors();
  return {
    displayColors: false,
    backgroundColor: tc.tooltipBg,
    borderColor: color || tc.tooltipBorder,
    borderWidth: 1,
    titleColor: tc.tooltipText,
    bodyColor: tc.tooltipText,
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

// -- Clean markdown & text formatter (removes raw asterisks, bolds **text**, styles `code`) --
function renderFormattedText(text: string, isBullet = false): React.ReactNode {
  if (!text) return null;
  let str = text.trim();
  if (isBullet) {
    str = str.replace(/^([•\-\*]+|\d+[\.\)])\s*/, "").trim();
  }

  // Match **bold text** or `code`
  const regex = /(\*\*[\s\S]+?\*\*|`[\s\S]+?`)/g;
  const parts = str.split(regex);

  return (
    <>
      {parts.map((part, idx) => {
        if (!part) return null;
        if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
          const inner = part.slice(2, -2).trim();
          return (
            <strong key={idx} className="font-bold text-slate-900 dark:text-slate-100">
              {inner}
            </strong>
          );
        }
        if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
          const inner = part.slice(1, -1).trim();
          return (
            <code
              key={idx}
              className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium mx-0.5"
              style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}
            >
              {inner}
            </code>
          );
        }
        // Remove any leftover stray double asterisks
        const cleanedPart = part.replace(/\*\*/g, "");
        return <span key={idx}>{cleanedPart}</span>;
      })}
    </>
  );
}

// -- Base chart options --
function baseOpts(color: string, xLabel = "", yLabel = "", horizontal = false): any {
  const tc = getChartThemeColors();
  const scaleBase = {
    ticks: { color: tc.text, font: { size: 11, weight: "bold" as const }, maxTicksLimit: 8 },
    grid: { color: tc.grid },
    border: { color: tc.border },
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
        type: horizontal ? ("linear" as const) : ("category" as const),
        title: {
          display: true,
          text: xLabel || (horizontal ? "Value" : "Category"),
          color: tc.text,
          font: { size: 12, weight: "bold" as const },
          padding: { top: 4 },
        },
        ticks: {
          ...scaleBase.ticks,
          callback: horizontal ? (v: any) => fmtN(Number(v)) : undefined,
        },
        beginAtZero: horizontal,
      },
      y: {
        ...scaleBase,
        type: horizontal ? ("category" as const) : ("linear" as const),
        title: {
          display: true,
          text: yLabel || (horizontal ? "Category" : "Value"),
          color: tc.text,
          font: { size: 12, weight: "bold" as const },
          padding: { bottom: 4 },
        },
        ticks: horizontal
          ? {
            color: tc.text,
            font: { size: 11, weight: "bold" as const },
            callback: function (this: any, val: any) {
              const lbl = this.getLabelForValue ? this.getLabelForValue(val) : val;
              const str = String(lbl ?? "");
              return str.length > 20 ? str.slice(0, 18) + "…" : str;
            },
          }
          : {
            ...scaleBase.ticks,
            callback: (v: any) => fmtN(Number(v)),
            maxTicksLimit: 6,
          },
        beginAtZero: !horizontal,
      },
    },
  };
}


// -- Safe chart_data parser helper --
function getChartData(ins: any): { labels: string[]; values: number[];[key: string]: any } | null {
  if (!ins || !ins.chart_data) return null;
  let cd = ins.chart_data;
  if (typeof cd === "string") {
    try { cd = JSON.parse(cd); } catch { return null; }
  }
  if (!cd || typeof cd !== "object") return null;

  let labels = cd.labels;
  let values = cd.values;
  if (typeof labels === "string") { try { labels = JSON.parse(labels); } catch { } }
  if (typeof values === "string") { try { values = JSON.parse(values); } catch { } }

  if (!Array.isArray(labels) || !Array.isArray(values) || labels.length === 0 || values.length === 0) {
    return null;
  }
  return { ...cd, labels, values };
}

// -- 9 Dedicated chart renderers --
function renderInsightChart(ins: any): React.ReactNode {
  const cd = getChartData(ins);
  const type = ins.type as string;
  const t = theme(type);
  const col = t.text;

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
            borderColor: sLabels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
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
            legend: {
              display: true, position: "right" as const, labels: {
                color: getChartThemeColors().text, font: { size: 11, weight: "bold" }, boxWidth: 12, padding: 12,
                generateLabels: (chart: any) => {
                  const ds = chart.data.datasets[0];
                  return (chart.data.labels || []).map((lbl: string, i: number) => {
                    const val = Number(ds.data[i]);
                    const pct = total > 0 ? ((Math.abs(val) / total) * 100).toFixed(1) : "0";
                    return { text: `${lbl} (${pct}%)`, fillStyle: PIE_PALETTE[i % PIE_PALETTE.length], strokeStyle: "rgba(0,0,0,0.3)", lineWidth: 1, index: i, hidden: false };
                  });
                },
              }
            },
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
            legend: { display: true, position: "right" as const, labels: { color: getChartThemeColors().text, font: { size: 11, weight: "bold" }, boxWidth: 12, padding: 12 } },
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
            borderColor: labels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
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
            borderColor: ["#6366f1", isUp ? "#10b981" : "#ef4444"],
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
            label: "Missing Count",
            data: values,
            backgroundColor: values.map(v => v > 50 ? "rgba(239,68,68,0.7)" : v > 10 ? "rgba(245,158,11,0.7)" : "rgba(34,197,94,0.7)"),
            borderColor: values.map(v => v > 50 ? "#ef4444" : v > 10 ? "#f59e0b" : "#22c55e"),
            borderWidth: 1.5, borderRadius: 4, borderSkipped: false as const,
          }],
        }}
        options={baseOpts(col, cd.y_label || "Missing Values", cd.x_label || "Column", true)}
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
            borderColor: sLabels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
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
            borderColor: values.map(v => v > 0 ? "#ef4444" : "#22c55e"),
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
          borderColor: labels.map((_, i) => PIE_PALETTE[i % PIE_PALETTE.length]),
          borderWidth: 1.5, borderRadius: 5, borderSkipped: false as const,
        }],
      }}
      options={baseOpts(col, yLabel, "Column", true)}
    />
  );
}

// -- Forecast Card — Full interactive predictive analytics card --
export function ForecastCard({ ins }: { ins: any }) {
  const [activeTab, setActiveTab] = useState<"forecast" | "decomp" | "models">("forecast");
  const [horizon, setHorizon] = useState<number | null>(null);
  const [runningForecast, setRunningForecast] = useState(false);
  const [localData, setLocalData] = useState<any>(null);
  const { uploadId } = useWorkspace();

  const cd = localData ?? (ins.chart_data && typeof ins.chart_data === "string" ? JSON.parse(ins.chart_data) : ins.chart_data);
  const stats = cd?.summary_stats || {};
  const mapes = cd?.model_mapes || {};
  const decomp = cd?.decomposition;
  const col = "#00d4ff";

  const histLabels = cd?.labels || [];
  const histValues = cd?.values || [];
  const fcLabels = cd?.forecast_labels || [];
  const fcValues = cd?.forecast_values || [];
  const upper95 = cd?.upper_95 || [];
  const lower95 = cd?.lower_95 || [];
  const upper80 = cd?.upper_80 || [];
  const lower80 = cd?.lower_80 || [];

  const allLabels = [...histLabels, ...fcLabels];
  const n_hist = histLabels.length;
  const n_fc = fcLabels.length;

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
          labels: d.historical_labels || [],
          values: d.historical_values || [],
          forecast_labels: d.forecast_labels || [],
          forecast_values: d.forecast_values || [],
          upper_95: d.upper_95 || [],
          lower_95: d.lower_95 || [],
          upper_80: d.upper_80 || [],
          lower_80: d.lower_80 || [],
          decomposition: d.decomposition,
          freq: d.freq,
          horizon: d.horizon,
          model_mapes: d.model_mapes || {},
          best_model: d.best_model,
          summary_stats: d.summary_stats || {},
        });
      }
    } catch (e) { console.error(e); }
    finally { setRunningForecast(false); }
  }, [uploadId, ins.metric]);

  const growthPct = stats.projected_growth_pct ?? 0;
  const isPositive = growthPct >= 0;
  const bestModel = cd?.best_model || "Ensemble";
  const mapeValues = Object.values(mapes as Record<string, number>);
  const avgMAPE = mapeValues.length > 0
    ? (mapeValues.reduce((a, b) => a + b, 0) / mapeValues.length).toFixed(1)
    : String(stats.avg_mape ?? "—");

  const HORIZONS = [
    { label: "7d", v: 7 },
    { label: "30d", v: 30 },
    { label: "90d", v: 90 },
    { label: "1yr", v: 365 },
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

  const tc = getChartThemeColors();
  const chartOpts: any = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500 },
    layout: { padding: { top: 4, right: 8, bottom: 4, left: 4 } },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: tc.text,
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
          color: tc.text,
          font: { size: 12, weight: "bold" },
          padding: { top: 4 },
        },
        ticks: { color: tc.text, font: { size: 11, weight: "bold" }, maxTicksLimit: 8 },
        grid: { color: tc.grid },
        border: { color: tc.border },
      },
      y: {
        title: {
          display: true,
          text: toLabel(ins.metric || "Value"),
          color: tc.text,
          font: { size: 12, weight: "bold" },
          padding: { bottom: 4 },
        },
        ticks: { color: tc.text, font: { size: 11, weight: "bold" }, callback: (v: any) => fmtN(Number(v)) },
        grid: { color: tc.grid },
        border: { color: tc.border },
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
        <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
          forecast model
        </span>
      </div>

      {/* Description */}
      <p className="px-5 pb-3 text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>{ins.description}</p>

      {/* Forecast Metric Tiles */}
      <div className="px-5 pb-4 grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="flex items-center gap-2 p-2 rounded-lg border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          {isPositive ? <TrendingUp size={14} style={{ color: "#10b981" }} /> : <TrendingDown size={14} style={{ color: "#ef4444" }} />}
          <div className="min-w-0">
            <span className="block text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Projected</span>
            <span className="block text-xs font-mono font-bold" style={{ color: isPositive ? "#10b981" : "#ef4444" }}>{isPositive ? "+" : ""}{growthPct.toFixed(1)}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2 p-2 rounded-lg border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          <Target size={14} className="text-cyan-500" />
          <div className="min-w-0">
            <span className="block text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>End Val</span>
            <span className="block text-xs font-mono font-bold" style={{ color: "var(--txt)" }}>{fmtN(stats.proj_end_val ?? 0)}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 p-2 rounded-lg border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          <Zap size={14} className="text-amber-500" />
          <div className="min-w-0">
            <span className="block text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Avg MAPE</span>
            <span className="block text-xs font-mono font-bold" style={{ color: "var(--txt)" }}>{avgMAPE}%</span>
          </div>
        </div>
        <div className="flex items-center gap-2 p-2 rounded-lg border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          <BarChart2 size={14} className="text-indigo-500" />
          <div className="min-w-0">
            <span className="block text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Horizon</span>
            <span className="block text-xs font-mono font-bold" style={{ color: "var(--txt)" }}>{stats.n_points ?? 0} pts</span>
          </div>
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
      <div className="mx-3 mb-4 rounded-xl p-3 border shadow-inner" style={{ background: "var(--card-bg, var(--surface))", borderColor: "var(--border)", height: 290, position: "relative" }}>
        {activeTab === "forecast" && (
          <>
            {runningForecast && (
              <div className="absolute inset-0 flex items-center justify-center z-10 rounded-xl" style={{ background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)" }}>
                <div className="flex flex-col items-center gap-2">
                  <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="#00d4ff" strokeWidth="4" /><path className="opacity-75" fill="#00d4ff" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
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
                { label: "Trend", data: decomp.trend, borderColor: "#6366f1", backgroundColor: "transparent", borderWidth: 2, pointRadius: 0, tension: 0.4 },
                { label: "Seasonal", data: decomp.seasonal, borderColor: "#10b981", backgroundColor: "transparent", borderWidth: 1.5, pointRadius: 0, tension: 0.4, borderDash: [4, 3] },
                { label: "Residual", data: decomp.residual, borderColor: "rgba(239,68,68,0.6)", backgroundColor: "transparent", borderWidth: 1, pointRadius: 0, tension: 0.3 },
              ],
            }}
            options={{ ...chartOpts, plugins: { ...chartOpts.plugins, legend: { display: true, labels: { color: tc.text, font: { size: 10, weight: "bold" }, boxWidth: 12 } } } }}
          />
        )}
        {activeTab === "decomp" && !decomp && (
          <div className="flex items-center justify-center h-full">
            <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>Decomposition not available for this dataset length.</p>
          </div>
        )}

        {activeTab === "models" && (
          <div className="h-full overflow-auto flex flex-col gap-3 px-2 py-4">
            <p className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: "var(--txt)" }}>Model Accuracy (MAPE — lower is better)</p>
            {Object.entries(mapes as Record<string, number>).map(([name, mape]) => {
              const isB = name === bestModel;
              const barW = Math.max(5, Math.min(100, 100 - mape));
              return (
                <div key={name} className="flex items-center gap-3">
                  <span className="text-[10px] font-bold flex-shrink-0" style={{ width: 120, color: isB ? "var(--accent)" : "var(--txt)" }}>
                    {name}{isB ? " ★" : ""}
                  </span>
                  <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                    <div className="h-full rounded-full transition-all" style={{ width: `${barW}%`, background: isB ? "linear-gradient(90deg,#00d4ff,#6366f1)" : "var(--txt-m)" }} />
                  </div>
                  <span className="text-[10px] font-mono font-bold" style={{ width: 60, textAlign: "right", color: isB ? "var(--accent)" : "var(--txt-m)" }}>{mape.toFixed(1)}% err</span>
                </div>
              );
            })}
            {Object.keys(mapes).length === 0 && (
              <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>No model metrics available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// -- Structured Visual for Dataset Overview / Profile Insights --
function DatasetProfileVisual({ ins }: { ins: any }) {
  const desc = ins.description || "";
  const rowsMatch = desc.match(/([\d,]+)\s+rows/i);
  const colsMatch = desc.match(/([\d,]+)\s+columns/i);
  const metricsMatch = desc.match(/(\d+)\s+numeric/i);
  const dimsMatch = desc.match(/(\d+)\s+categorical/i);
  const dateMatch = desc.match(/date column:\s*'([^']+)'/i);
  const domainMatch = desc.match(/classified as:\s*([a-zA-Z0-9_\-]+)/i);

  const rows = rowsMatch ? rowsMatch[1] : (ins.sample_size ? ins.sample_size.toLocaleString() : "—");
  const cols = colsMatch ? colsMatch[1] : "—";
  const metrics = metricsMatch ? metricsMatch[1] : "0";
  const dims = dimsMatch ? dimsMatch[1] : "0";
  const dateCol = dateMatch ? dateMatch[1] : "None detected";
  const domain = domainMatch ? domainMatch[1] : "general";

  return (
    <div
      className="mx-3 mb-3 p-3.5 rounded-xl border flex flex-col justify-between"
      style={{
        background: "var(--surface)",
        borderColor: "var(--border)",
        minHeight: 230,
      }}
    >
      <div className="grid grid-cols-2 gap-2">
        <div className="p-2.5 rounded-lg border flex flex-col justify-center" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Total Rows</span>
          <span className="text-base font-black font-mono mt-0.5" style={{ color: "var(--txt)" }}>{rows}</span>
        </div>
        <div className="p-2.5 rounded-lg border flex flex-col justify-center" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Total Columns</span>
          <span className="text-base font-black font-mono mt-0.5" style={{ color: "var(--txt)" }}>{cols}</span>
        </div>
        <div className="p-2.5 rounded-lg border flex flex-col justify-center" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Dimensions</span>
          <span className="text-base font-black font-mono mt-0.5 text-indigo-500">{dims}</span>
        </div>
        <div className="p-2.5 rounded-lg border flex flex-col justify-center" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
          <span className="text-[9px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Metrics</span>
          <span className="text-base font-black font-mono mt-0.5 text-emerald-500">{metrics}</span>
        </div>
      </div>

      <div className="pt-2.5 mt-2 border-t flex flex-col gap-1.5 text-[11px]" style={{ borderColor: "var(--border)" }}>
        <div className="flex justify-between items-center">
          <span className="font-semibold text-[10px]" style={{ color: "var(--txt-m)" }}>Temporal Anchor:</span>
          <span className="font-mono font-bold text-[10px] truncate max-w-[150px] px-1.5 py-0.5 rounded border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)", color: "var(--txt)" }}>
            {dateCol}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="font-semibold text-[10px]" style={{ color: "var(--txt-m)" }}>Domain Classification:</span>
          <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--txt)" }}>
            {domain}
          </span>
        </div>
      </div>
    </div>
  );
}

// -- Insight Card (Section 4.2 Standard Finding Representation) --
export function InsightCard({
  ins,
  idx,
  isPinned = false,
  onTogglePin,
  onDismiss,
}: {
  ins: any;
  idx: number;
  isPinned?: boolean;
  onTogglePin?: (ins: any) => void;
  onDismiss?: (id: string) => void;
}) {
  // Forecast insights get their own dedicated card
  if (ins.type === "forecast") return <ForecastCard ins={ins} />;

  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const t = theme(ins.type);
  const imp = Math.round((ins.importance ?? 0) * 100);
  const cd = getChartData(ins);
  const hasChart = !!cd;
  const insId = ins.id || ins.title || `ins-${idx}`;

  return (
    <div
      className="rounded-2xl overflow-hidden flex flex-col transition-all duration-200"
      style={{
        background: "var(--surface)",
        border: `1px solid ${t.border}`,
        boxShadow: `0 4px 24px rgba(0,0,0,0.25), 0 0 0 1px ${t.border}`,
      }}
    >
      {/* Colour accent bar */}
      <div className="h-[3px] w-full" style={{ background: `linear-gradient(90deg,${t.text},${t.text}44)` }} />

      {/* Header */}
      <div className="px-4 pt-4 pb-2 flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="font-black text-sm leading-tight truncate" title={ins.title} style={{ color: "var(--txt)" }}>{ins.title}</p>
            {ins.is_protected && (
              <span className="text-[10px] font-semibold" style={{ color: "var(--warn-fg, #f59e0b)" }}>
                · Demographic Segment
              </span>
            )}
          </div>
          {ins.metric && <p className="text-[9px] font-mono mt-0.5" style={{ color: "var(--txt-m)" }}>{ins.metric}</p>}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <span className="text-[10px] font-medium tracking-wider uppercase" style={{ color: "var(--txt-m)" }}>
            {ins.type?.replace(/_/g, " ")}
          </span>

          {onTogglePin && (
            <button
              onClick={() => onTogglePin(ins)}
              title={isPinned ? "Unpin from Dashboard" : "Pin finding to Dashboard"}
              className={`p-1.5 rounded-lg text-xs transition-all cursor-pointer border ${isPinned
                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                : "bg-white/5 hover:bg-white/10 text-slate-400 border-white/10"
                }`}
            >
              <Pin size={11} className={isPinned ? "fill-amber-400 text-amber-400" : ""} />
            </button>
          )}

          {onDismiss && (
            <button
              onClick={() => onDismiss(insId)}
              title="Dismiss this finding"
              className="p-1.5 rounded-lg text-xs text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-all cursor-pointer border border-white/10"
            >
              <X size={11} />
            </button>
          )}
        </div>
      </div>

      {/* Description with clean markdown rendering */}
      <p className="px-4 pb-2 text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
        {renderFormattedText(ins.description)}
      </p>

      {/* Importance bar */}
      <div className="px-4 pb-3 flex items-center gap-2">
        <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Relevance</span>
        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--inp-bg)" }}>
          <div className="h-full rounded-full transition-all" style={{ width: `${imp}%`, background: `linear-gradient(90deg,${t.text},${t.text}88)` }} />
        </div>
        <span className="font-mono text-[10px] font-bold" style={{ color: t.text }}>{imp}%</span>
      </div>

      {/* Visual Content: Chart or Structured Profile */}
      {hasChart ? (
        <div className="mx-3 mb-3 rounded-xl p-3 border shadow-inner" style={{ background: "var(--card-bg, var(--surface))", borderColor: "var(--border)", height: 230, position: "relative" }}>
          {renderInsightChart(ins)}
        </div>
      ) : ins.type === "profile" ? (
        <DatasetProfileVisual ins={ins} />
      ) : null}

      {/* Evidence & Verification Drawer (Section 4.2 & 5.1) */}
      <div className="mt-auto border-t px-4 py-2.5 transition-all" style={{ borderColor: "var(--border)", background: "var(--inp-bg)" }}>
        <button
          onClick={() => setEvidenceOpen(o => !o)}
          className="w-full flex items-center justify-between text-[10px] font-bold uppercase tracking-wider transition-colors cursor-pointer"
          style={{ color: "var(--txt-m)" }}
        >
          <span className="flex items-center gap-1.5">
            <Shield size={11} className="text-indigo-500" />
            Evidence &amp; Statistical Support
          </span>
          <ChevronDown size={11} className={`transform transition-transform ${evidenceOpen ? "rotate-180" : ""}`} />
        </button>

        {evidenceOpen && (
          <div className="pt-2.5 mt-2 border-t space-y-2 text-[10px]" style={{ borderColor: "var(--border)" }}>
            {ins.sample_size && (
              <div className="flex justify-between font-mono">
                <span style={{ color: "var(--txt-m)" }}>Sample Size (N):</span>
                <span className="font-bold" style={{ color: "var(--txt)" }}>{ins.sample_size.toLocaleString()} rows</span>
              </div>
            )}
            {ins.evidence_query && (
              <div className="space-y-1">
                <span className="font-mono font-medium" style={{ color: "var(--txt-m)" }}>Evidence Query:</span>
                <pre
                  className="p-2.5 rounded-lg font-mono text-[10px] overflow-x-auto select-all"
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                    color: "var(--txt)",
                  }}
                >
                  {ins.evidence_query}
                </pre>
              </div>
            )}
            {ins.caveats && ins.caveats.length > 0 && (
              <div className="space-y-0.5">
                <span className="font-medium" style={{ color: "var(--txt-m)" }}>Caveats &amp; Honesty Note:</span>
                <ul className="list-disc list-inside text-amber-600 font-medium text-[9.5px] space-y-0.5">
                  {ins.caveats.map((c: string, ci: number) => (
                    <li key={ci}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// -- Column Roles & Semantic Review Modal (Section 4.1 & 5.1) --
function ColumnRolesModal({
  isOpen,
  onClose,
  schema,
  columns,
  uploadId,
  onRolesSaved,
}: {
  isOpen: boolean;
  onClose: () => void;
  schema: any;
  columns: any[];
  uploadId: string;
  onRolesSaved: () => void;
}) {
  const [roles, setRoles] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (schema?.column_roles) {
      const initial: Record<string, string> = {};
      Object.entries(schema.column_roles).forEach(([col, meta]: [string, any]) => {
        initial[col] = meta.role || "segment";
      });
      setRoles(initial);
    }
  }, [schema]);

  if (!isOpen) return null;

  const colList = (columns || []).map((c: any) => c.name || c);

  const saveRoles = async () => {
    setIsSaving(true);
    try {
      await apiFetch("/insights/roles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, column_roles: roles }),
      });
      onRolesSaved();
      onClose();
    } catch (e) {
      console.error(e);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl border flex flex-col max-h-[85vh] overflow-hidden" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
        <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Tag size={15} />
            </div>
            <div>
              <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>Semantic Column Roles &amp; Tags</h3>
              <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>Correct or customize semantic tags. Changes persist per dataset.</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg cursor-pointer" style={{ color: "var(--txt-m)" }}><X size={16} /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b text-[9px] uppercase tracking-wider" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
                <th className="pb-2">Column Name</th>
                <th className="pb-2">Current Role</th>
                <th className="pb-2">Override Semantic Role</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
              {colList.map(col => {
                const currentRole = roles[col] || schema?.column_roles?.[col]?.role || "auto";
                return (
                  <tr key={col} className="py-2">
                    <td className="py-2.5 font-bold" style={{ color: "var(--txt)" }}>{col}</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase border" style={{ background: "var(--inp-bg)", color: "var(--txt-m)", borderColor: "var(--border)" }}>
                        {currentRole}
                      </span>
                    </td>
                    <td className="py-2.5">
                      <select
                        value={currentRole}
                        onChange={e => setRoles(r => ({ ...r, [col]: e.target.value }))}
                        className="px-2 py-1 rounded border text-xs font-sans outline-none"
                        style={{ background: "var(--inp-bg)", borderColor: "var(--border)", color: "var(--txt)" }}
                      >
                        <option value="kpi">Measure / KPI</option>
                        <option value="driver">Candidate Driver</option>
                        <option value="segment">Segment / Dimension</option>
                        <option value="time">Time / Date</option>
                        <option value="identifier">Identifier (Excluded from drivers)</option>
                        <option value="protected">Protected Attribute (Demographic only)</option>
                        <option value="ignore">Ignore / Suppress</option>
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="px-6 py-4 border-t flex justify-end gap-2" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-bold cursor-pointer" style={{ color: "var(--txt-m)" }}>Cancel</button>
          <button
            onClick={saveRoles}
            disabled={isSaving}
            className="px-5 py-2 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-all cursor-pointer"
          >
            {isSaving ? "Saving..." : "Save Roles & Re-Run Analysis"}
          </button>
        </div>
      </div>
    </div>
  );
}




// ── Redesigned Executive Briefing Card (Section 4.4 Verified Narrative) ───────────
function ExecutiveBriefingCard({
  summary,
  targetMetric,
  focusPrompt,
}: {
  summary: string;
  targetMetric?: string;
  focusPrompt?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!summary) return;
    navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sections = useMemo(() => {
    if (!summary) return [];

    const CANONICAL_SECTIONS = [
      {
        key: "takeaway",
        title: "Executive Takeaway",
        iconType: "takeaway",
        badge: "Executive Summary",
        pattern: /^(?:[#*\-•\s\d.)]+)?(?:executive takeaway|executive summary|core takeaway|key takeaway|core synthesis|executive intelligence briefing)[*:\s]*$/i,
        inlinePattern: /^(?:[#*\-•\s\d.)]+)?(?:executive takeaway|executive summary|core takeaway|key takeaway|core synthesis|executive intelligence briefing)[*:\s]+(.+)$/i,
      },
      {
        key: "drivers",
        title: "Key Drivers & Dynamics",
        iconType: "driver",
        badge: "Drivers & Dynamics",
        pattern: /^(?:[#*\-•\s\d.)]+)?(?:key drivers\s*(?:&|and)?\s*dynamics|key drivers\s*(?:&|and)?\s*correlation dynamics|key drivers|correlation dynamics|underlying drivers)[*:\s]*$/i,
        inlinePattern: /^(?:[#*\-•\s\d.)]+)?(?:key drivers\s*(?:&|and)?\s*dynamics|key drivers\s*(?:&|and)?\s*correlation dynamics|key drivers|correlation dynamics|underlying drivers)[*:\s]+(.+)$/i,
      },
      {
        key: "strategy",
        title: "Strategic Recommendations",
        iconType: "action",
        badge: "Strategy",
        pattern: /^(?:[#*\-•\s\d.)]+)?(?:strategic recommendations|strategic recommendation|recommendations|operational next steps|action items|recommended actions)[*:\s]*$/i,
        inlinePattern: /^(?:[#*\-•\s\d.)]+)?(?:strategic recommendations|strategic recommendation|recommendations|operational next steps|action items|recommended actions)[*:\s]+(.+)$/i,
      },
      {
        key: "quality",
        title: "Data Quality & Completeness",
        iconType: "quality",
        badge: "Integrity",
        pattern: /^(?:[#*\-•\s\d.)]+)?(?:data quality\s*(?:&|and)?\s*completeness|data quality|data completeness|data integrity)[*:\s]*$/i,
        inlinePattern: /^(?:[#*\-•\s\d.)]+)?(?:data quality\s*(?:&|and)?\s*completeness|data quality|data completeness|data integrity)[*:\s]+(.+)$/i,
      },
      {
        key: "trend",
        title: "Performance Trajectory",
        iconType: "trend",
        badge: "Dynamics",
        pattern: /^(?:[#*\-•\s\d.)]+)?(?:performance trajectory|performance trends|secular trends|trend dynamics)[*:\s]*$/i,
        inlinePattern: /^(?:[#*\-•\s\d.)]+)?(?:performance trajectory|performance trends|secular trends|trend dynamics)[*:\s]+(.+)$/i,
      },
      {
        key: "context",
        title: "Demographic & Segment Context",
        iconType: "context",
        badge: "Cohort Context",
        pattern: /^(?:[#*\-•\s\d.)]+)?(?:demographic\s*(?:&|and)?\s*segment context|demographic context|segment context|cohort context)[*:\s]*$/i,
        inlinePattern: /^(?:[#*\-•\s\d.)]+)?(?:demographic\s*(?:&|and)?\s*segment context|demographic context|segment context|cohort context)[*:\s]+(.+)$/i,
      },
      {
        key: "risk",
        title: "Risk Assessment & Anomalies",
        iconType: "risk",
        badge: "Risk & Caution",
        pattern: /^(?:[#*\-•\s\d.)]+)?(?:risk assessment\s*(?:&|and)?\s*anomalies|risk assessment|risks\s*(?:&|and)?\s*anomalies|anomalies\s*(?:&|and)?\s*outliers)[*:\s]*$/i,
        inlinePattern: /^(?:[#*\-•\s\d.)]+)?(?:risk assessment\s*(?:&|and)?\s*anomalies|risk assessment|risks\s*(?:&|and)?\s*anomalies|anomalies\s*(?:&|and)?\s*outliers)[*:\s]+(.+)$/i,
      },
    ];

    const lines = summary.split("\n");
    const parsed: { title: string; bullets: string[]; iconType: string; badge?: string }[] = [];
    let curSection: { title: string; bullets: string[]; iconType: string; badge?: string } | null = null;

    for (let rawLine of lines) {
      const line = rawLine.trim();
      if (
        !line ||
        line.startsWith("═") ||
        /^#*\s*executive\s+(?:intelligence\s+|strategic\s+)?briefing/i.test(line) ||
        /^#*\s*dataset\s+.*analysis/i.test(line) ||
        /^#*\s*executive\s+summary\s*[:\-]\s*dataset/i.test(line) ||
        /^user hypothesis inquiry:/i.test(line)
      ) continue;

      // 1. Check Canonical Standalone Header (e.g. "1. Executive Takeaway:", "**Executive Takeaway:**", "### 2. Key Drivers & Dynamics:")
      let standaloneMatch = false;
      for (const s of CANONICAL_SECTIONS) {
        if (s.pattern.test(line)) {
          curSection = {
            title: s.title,
            bullets: [],
            iconType: s.iconType,
            badge: s.badge,
          };
          parsed.push(curSection);
          standaloneMatch = true;
          break;
        }
      }
      if (standaloneMatch) continue;

      // 2. Check Inline Canonical Header (e.g. "**1. Executive Takeaway:** Narrative begins here...")
      let inlineHandled = false;
      for (const s of CANONICAL_SECTIONS) {
        const m = line.match(s.inlinePattern);
        if (m && m[1]) {
          curSection = {
            title: s.title,
            bullets: [m[1].trim()],
            iconType: s.iconType,
            badge: s.badge,
          };
          parsed.push(curSection);
          inlineHandled = true;
          break;
        }
      }
      if (inlineHandled) continue;

      // 3. Check Generic Standalone Header (e.g. "### Regional Findings:", "Next Steps:")
      const stripped = line
        .replace(/^[#*\-•\s\d.)]+/, "")
        .replace(/[:#*]+$/, "")
        .replace(/\*\*/g, "")
        .trim();

      const isGenericHeader =
        (line.startsWith("###") ||
          line.startsWith("##") ||
          line.endsWith(":") ||
          line.endsWith(":**") ||
          line.endsWith("**:")) &&
        stripped.length > 2 &&
        stripped.length < 70 &&
        !stripped.slice(0, -1).includes(".");

      if (isGenericHeader) {
        let cleanTitle = stripped;
        if (cleanTitle === cleanTitle.toUpperCase() && cleanTitle.length > 3) {
          cleanTitle = cleanTitle.toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
        }

        let iconType = "activity";
        let badge = undefined;
        const low = cleanTitle.toLowerCase();
        if (low.includes("quality") || low.includes("completeness") || low.includes("integrity")) {
          iconType = "quality";
          badge = "Integrity";
        } else if (low.includes("trajectory") || low.includes("performance") || low.includes("trend") || low.includes("dynamics")) {
          iconType = "trend";
          badge = "Dynamics";
        } else if (low.includes("driver") || low.includes("correlation") || low.includes("contribution")) {
          iconType = "driver";
          badge = "Drivers";
        } else if (low.includes("demographic") || low.includes("segment") || low.includes("context") || low.includes("cohort")) {
          iconType = "context";
          badge = "Cohort Context";
        } else if (low.includes("risk") || low.includes("anomal") || low.includes("outlier") || low.includes("caution")) {
          iconType = "risk";
          badge = "Risk & Caution";
        } else if (low.includes("action") || low.includes("suggest") || low.includes("prescript") || low.includes("recommend") || low.includes("strategic") || low.includes("priority")) {
          iconType = "action";
          badge = "Strategy";
        } else if (low.includes("takeaway") || low.includes("executive") || low.includes("synthesis") || low.includes("headline") || low.includes("core")) {
          iconType = "takeaway";
          badge = "Executive Summary";
        }

        curSection = { title: cleanTitle, bullets: [], iconType, badge };
        parsed.push(curSection);
        continue;
      }

      // 4. Regular Bullet or Narrative Content
      const bulletText = line.replace(/^([•\-\*]+|\d+[\.\)])\s*/, "").trim();
      if (bulletText) {
        // Discard standalone document titles mistakenly treated as bullet points
        const isDocTitle =
          /^executive (?:intelligence )?briefing[:\s]/i.test(bulletText) ||
          /^dataset ['"].*['"] analysis/i.test(bulletText) ||
          (bulletText.length < 50 && !bulletText.includes(" ") && bulletText.includes(".csv"));
        if (isDocTitle) continue;

        if (curSection) {
          curSection.bullets.push(bulletText);
        } else {
          // If no section header was encountered yet, initialize an Executive Takeaway section
          curSection = { title: "Executive Takeaway", bullets: [bulletText], iconType: "takeaway", badge: "Executive Summary" };
          parsed.push(curSection);
        }
      }
    }

    // Deduplicate sections with the same title and filter out empty sections
    const merged: { title: string; bullets: string[]; iconType: string; badge?: string }[] = [];
    for (const s of parsed) {
      const validBullets = s.bullets.filter(b => b && b.length > 5 && !/^executive briefing/i.test(b));
      if (!validBullets.length) continue;
      const existing = merged.find(m => m.title.trim().toLowerCase() === s.title.trim().toLowerCase());
      if (existing) {
        existing.bullets.push(...validBullets);
      } else {
        merged.push({ ...s, bullets: validBullets });
      }
    }

    return merged;
  }, [summary]);

  return (
    <div
      className="rounded-2xl p-5 md:p-6 space-y-5 border relative overflow-hidden"
      style={{
        background: "linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.04) 50%, rgba(16, 185, 129, 0.04) 100%)",
        borderColor: "rgba(99, 102, 241, 0.25)",
        boxShadow: "0 4px 24px rgba(99, 102, 241, 0.08)",
      }}
    >
      {/* Top Banner Header */}
      <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 text-white shadow-md shadow-indigo-500/20" style={{ background: "linear-gradient(135deg, #6366f1, #8b5cf6)" }}>
            <Brain size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>AI Executive Briefing</h3>
            </div>
            <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>Automated synthesis anchored to computed statistical findings</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {targetMetric && (
            <span className="text-[11px] font-bold px-2.5 py-1 rounded-lg border flex items-center gap-1" style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt-m)" }}>
              <Target size={12} className="text-indigo-500" /> Target KPI: <span className="font-mono font-bold" style={{ color: "var(--txt)" }}>{targetMetric}</span>
            </span>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition-all cursor-pointer"
            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
            title="Copy briefing to clipboard"
          >
            {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      </div>

      {/* Inquiry Callout if user entered steering prompt */}
      {focusPrompt && (
        <div className="px-3.5 py-2 rounded-xl border flex items-center gap-2 text-xs" style={{ background: "var(--inp-bg)", borderColor: "var(--border)", color: "var(--txt)" }}>
          <Sparkles size={13} className="text-amber-500 shrink-0" />
          <span>Active Investigation Hypothesis: <strong className="font-semibold" style={{ color: "var(--txt)" }}>"{focusPrompt}"</strong></span>
        </div>
      )}

      {/* Structured Sections Grid */}
      {sections.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sections.map((sec, i) => {
            const isQuality = sec.iconType === "quality";
            const isDriver = sec.iconType === "driver";
            const isRisk = sec.iconType === "risk";
            const isContext = sec.iconType === "context";
            const isTrend = sec.iconType === "trend";
            const isAction = sec.iconType === "action";

            const accentColor = isQuality
              ? "#10b981"
              : isDriver
                ? "#6366f1"
                : isRisk
                  ? "#ef4444"
                  : isContext
                    ? "#8b5cf6"
                    : isTrend
                      ? "#06b6d4"
                      : isAction
                        ? "#f59e0b"
                        : "#6366f1";

            return (
              <div
                key={i}
                className={`rounded-xl p-4 border transition-all flex flex-col justify-between ${sections.length === 3 && i === 0 ? "md:col-span-2" : ""
                  }`}
                style={{
                  background: "var(--surface)",
                  borderColor: "var(--border)",
                }}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2.5 pb-2 border-b" style={{ borderColor: "var(--border)" }}>
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full shadow-sm shrink-0" style={{ background: accentColor, boxShadow: `0 0 8px ${accentColor}80` }} />
                      <h4 className="text-xs font-black tracking-wide" style={{ color: "var(--txt)" }}>{sec.title}</h4>
                    </div>
                    {sec.badge && (
                      <span
                        className="text-[9px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider shrink-0"
                        style={{ background: `${accentColor}18`, color: accentColor, border: `1px solid ${accentColor}30` }}
                      >
                        {sec.badge}
                      </span>
                    )}
                  </div>
                  <div className="space-y-2.5">
                    {sec.bullets.map((b, bIdx) => {
                      const isSingleLongPara = sec.bullets.length === 1 && b.length > 100;
                      return (
                        <div key={bIdx} className="text-xs leading-relaxed flex items-start gap-2.5" style={{ color: "var(--txt-m)" }}>
                          {!isSingleLongPara && (
                            <span className="mt-1 shrink-0 font-bold text-[10px]" style={{ color: accentColor }}>•</span>
                          )}
                          <div className="flex-1 min-w-0">{renderFormattedText(b, true)}</div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-xs leading-relaxed whitespace-pre-line" style={{ color: "var(--txt)" }}>{renderFormattedText(summary)}</div>
      )}
    </div>
  );
}

// -- Main Tab (Section 5.1 Insights UX) --
export function InsightsTab() {
  const { profile, uploadId } = useWorkspace();
  const [insightTopN, setInsightTopN] = useState("9");
  const [targetMetric, setTargetMetric] = useState("");
  const [focusPrompt, setFocusPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [insightError, setInsightError] = useState("");
  const [insightCards, setInsightCards] = useState<any[]>([]);
  const [insightSummary, setInsightSummary] = useState("");
  const [insightSchema, setInsightSchema] = useState<any>(null);
  const [pinnedIds, setPinnedIds] = useState<string[]>([]);
  const [dismissedIds, setDismissedIds] = useState<string[]>([]);
  const [rolesModalOpen, setRolesModalOpen] = useState(false);

  // Load current insights and pinned state
  useEffect(() => {
    if (!uploadId) return;
    apiFetch(`/insights/current?upload_id=${uploadId}`)
      .then(res => res.ok ? res.json() : null)
      .then(d => {
        if (d && d.insights && Array.isArray(d.insights) && d.insights.length > 0) {
          setInsightCards(d.insights);
          setInsightSummary(d.summary || "");
          setInsightSchema(d.schema || null);
          if (d.schema?.primary_kpi && !targetMetric) {
            setTargetMetric(d.schema.primary_kpi);
          }
        }
      })
      .catch(console.error);

    // Fetch existing pinned insights to sync pin state
    apiFetch(`/dashboard/agentic-auto`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ upload_id: uploadId }),
    })
      .then(res => res.ok ? res.json() : null)
      .then(d => {
        if (d && Array.isArray(d.pinned_insights)) {
          setPinnedIds(d.pinned_insights.map((p: any) => p.id || p.title));
        }
      })
      .catch(() => { });
  }, [uploadId]);

  const togglePin = async (ins: any) => {
    if (!uploadId) return;
    const insId = ins.id || ins.title;
    const isPinned = pinnedIds.includes(insId);
    const action = isPinned ? "unpin" : "pin";

    try {
      const res = await apiFetch("/dashboard/pin-insight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, insight: ins, action }),
      });
      if (res.ok) {
        setPinnedIds(prev => isPinned ? prev.filter(id => id !== insId) : [...prev, insId]);
      }
    } catch (e) {
      console.error("Pinning insight failed:", e);
    }
  };

  const dismissFinding = (id: string) => {
    setDismissedIds(prev => [...prev, id]);
  };

  const runInsights = async (customPrompt?: string, countOverride?: number) => {
    setIsRunning(true);
    setInsightError("");
    // Keep existing cards and summary while running if they exist, so no screen-wiping / flashing
    const activePrompt = customPrompt !== undefined ? customPrompt : focusPrompt;
    const targetN = countOverride || parseInt(insightTopN, 10) || 6;

    try {
      const res = await apiFetch("/insights/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          top_n: targetN,
          use_gemini: true,
          upload_id: uploadId,
          target_metric: targetMetric || undefined,
          focus_prompt: activePrompt ? activePrompt.trim() : undefined,
        }),
      });

      if (!res.ok) {
        const text = await res.text();
        let msg = `HTTP ${res.status}`;
        try { const d = JSON.parse(text); msg = d.detail || d.error || msg; } catch { msg = text.substring(0, 150) || msg; }
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

  const kpiCandidates = insightSchema?.kpi_candidates?.length
    ? insightSchema.kpi_candidates
    : (insightSchema?.metrics || profile?.columns?.filter((c: any) => c.dtype?.includes("int") || c.dtype?.includes("float")).map((c: any) => c.name) || []);

  const visibleCards = insightCards.filter(ins => !dismissedIds.includes(ins.id || ins.title));
  const targetCount = parseInt(insightTopN, 10) || 6;
  const displayedCards = visibleCards.slice(0, targetCount);

  // -- Empty state --
  if (!insightCards.length && !isRunning) return (
    <div className="tab-panel px-4 py-6 md:px-6">
      <div className="flex items-center justify-between mb-8 flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Insight Engine</h2>
          <p className="text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>Trends · Anomalies · Correlations · Rankings · Distributions · Contributions</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center p-0.5 rounded-xl border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
            {[3, 6, 9].map(n => {
              const active = parseInt(insightTopN, 10) === n;
              return (
                <button
                  key={n}
                  type="button"
                  onClick={() => setInsightTopN(String(n))}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${active
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                    }`}
                >
                  {n} Findings
                </button>
              );
            })}
          </div>
          <button onClick={() => runInsights()} className="bp flex items-center gap-2 cursor-pointer"><Sparkles size={14} /> Run Insights</button>
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
          <p className="font-black text-base mb-1" style={{ color: "var(--txt)" }}>No Insights Generated Yet</p>
          <p className="text-sm max-w-sm" style={{ color: "var(--txt-m)" }}>Click <strong>Run Insights</strong> to discover verified statistical signals, anchored correlations, and distribution findings.</p>
        </div>
        <button onClick={() => runInsights()} className="px-6 py-3 rounded-xl font-bold text-sm text-white cursor-pointer" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>Run Insights</button>
      </div>
    </div>
  );

  // -- Loading skeleton --
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

  // -- Results --
  return (
    <div className="tab-panel space-y-6 px-4 py-4 md:px-6 md:py-6">
      {/* Header & Controls */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>Insight Engine</h2>

        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Target KPI Anchor Selector (Section 4.1 & 5.1) */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
            <Target size={13} className="text-amber-500" />
            <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Anchor KPI:</span>
            <select
              value={targetMetric}
              onChange={e => {
                setTargetMetric(e.target.value);
              }}
              className="bg-transparent border-none outline-none font-bold text-xs cursor-pointer"
              style={{ color: "var(--txt)" }}
            >
              <option value="" style={{ background: "var(--surface)", color: "var(--txt)" }}>
                Auto-Detect ({insightSchema?.primary_kpi || "None"})
              </option>
              {kpiCandidates.map((k: string) => (
                <option key={k} value={k} style={{ background: "var(--surface)", color: "var(--txt)" }}>{k}</option>
              ))}
            </select>
          </div>

          {/* Semantic Roles Review Button */}
          <button
            onClick={() => setRolesModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all cursor-pointer"
            style={{ borderColor: "var(--border)", background: "var(--surface)", color: "var(--txt)" }}
          >
            <Tag size={12} className="text-indigo-500" /> Review Roles
          </button>

          {/* Top-N Count Selector: 3, 6, 9 */}
          <div className="flex items-center p-0.5 rounded-xl border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
            {[3, 6, 9].map(n => {
              const active = parseInt(insightTopN, 10) === n;
              return (
                <button
                  key={n}
                  type="button"
                  onClick={() => {
                    setInsightTopN(String(n));
                    if (visibleCards.length < n) {
                      runInsights(undefined, n);
                    }
                  }}
                  className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${active
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "hover:bg-slate-500/10"
                    }`}
                  style={!active ? { color: "var(--txt-m)" } : undefined}
                >
                  {n} Findings
                </button>
              );
            })}
          </div>

          <button onClick={() => runInsights()} disabled={isRunning} className="bp flex items-center gap-1.5 cursor-pointer">
            {isRunning
              ? <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              : <Sparkles size={13} />
            }
            {isRunning ? "Analysing…" : "Re-Analyze"}
          </button>
        </div>
      </div>

      {/* Investigate with AI Steering Bar (Section 4.5 & 5.1) */}
      <div className="rounded-2xl p-4 border" style={{ background: "linear-gradient(135deg,rgba(99,102,241,0.06),rgba(139,92,246,0.03))", borderColor: "rgba(99,102,241,0.2)" }}>
        <form onSubmit={e => { e.preventDefault(); runInsights(); }} className="flex gap-2 items-center flex-wrap">
          <div
            className="flex items-center gap-2 flex-1 min-w-[260px] border rounded-xl px-3 py-2 transition-all"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--txt)",
            }}
          >
            <Sparkles size={14} className="text-indigo-500 shrink-0" />
            <input
              type="text"
              value={focusPrompt}
              onChange={e => setFocusPrompt(e.target.value)}
              placeholder="Investigate hypothesis or steer analysis, e.g. 'Investigate margin decline in North region'..."
              className="bg-transparent border-none outline-none w-full text-xs font-sans"
              style={{ color: "var(--txt)" }}
            />
            {focusPrompt && (
              <button type="button" onClick={() => setFocusPrompt("")} className="cursor-pointer opacity-60 hover:opacity-100" style={{ color: "var(--txt-m)" }}>
                <X size={12} />
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={isRunning}
            className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 flex items-center gap-1.5 cursor-pointer shrink-0"
          >
            <Sparkles size={12} />
            {isRunning ? "Investigating..." : "Steer Analysis"}
          </button>
        </form>
      </div>

      {/* Executive Briefing (Section 4.4 Verified Narrative) */}
      {insightSummary && (
        <ExecutiveBriefingCard
          summary={insightSummary}
          targetMetric={targetMetric}
          focusPrompt={focusPrompt}
        />
      )}

      {insightError && (
        <div className="p-4 rounded-xl font-mono text-sm text-red-400" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>{insightError}</div>
      )}

      {/* Cards Grid with Pinning, Dismissal, and Evidence Drawer */}
      {displayedCards.filter(ins => ins.type === "forecast").map((ins, i) => (
        <InsightCard
          key={`fc-${i}`}
          ins={ins}
          idx={i}
          isPinned={pinnedIds.includes(ins.id || ins.title)}
          onTogglePin={togglePin}
          onDismiss={dismissFinding}
        />
      ))}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {displayedCards.filter(ins => ins.type !== "forecast").map((ins, i) => (
          <InsightCard
            key={ins.id || `card-${i}`}
            ins={ins}
            idx={i}
            isPinned={pinnedIds.includes(ins.id || ins.title)}
            onTogglePin={togglePin}
            onDismiss={dismissFinding}
          />
        ))}
      </div>

      {/* Semantic Roles Modal */}
      <ColumnRolesModal
        isOpen={rolesModalOpen}
        onClose={() => setRolesModalOpen(false)}
        schema={insightSchema}
        columns={profile?.columns || []}
        uploadId={uploadId || ""}
        onRolesSaved={() => runInsights()}
      />
    </div>
  );
}

