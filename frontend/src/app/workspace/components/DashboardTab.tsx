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
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import {
  RefreshCw,
  X,
  Pin,
  BarChart4,
  TrendingUp,
  TrendingDown,
  Minus,
  Plus,
  Layers,
  PieChart,
  Activity,
  GitBranch,
  Download,
  Palette,
  Maximize2,
  Bot,
  Sparkles,
  LayoutDashboard,
  Target,
} from "lucide-react";
import { Scatter, Line, Bar, Pie, Doughnut, Radar, PolarArea } from "react-chartjs-2";
import { ForecastCard, InsightCard } from "./InsightsTab";

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, RadialLinearScale, Title, Tooltip, Legend, Filler
);

export const PALETTES: Record<string, { name: string; colors: string[] }> = {
  indigo: {
    name: "Neon Indigo",
    colors: ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899", "#f97316", "#84cc16", "#14b8a6"],
  },
  sapphire: {
    name: "Sapphire Corporate",
    colors: ["#2563eb", "#0284c7", "#06b6d4", "#3b82f6", "#1d4ed8", "#60a5fa", "#0ea5e9", "#38bdf8", "#0369a1", "#075985"],
  },
  emerald: {
    name: "Emerald Forest",
    colors: ["#059669", "#10b981", "#34d399", "#047857", "#0d9488", "#14b8a6", "#2dd4bf", "#15803d", "#16a34a", "#22c55e"],
  },
  cyberpunk: {
    name: "Cyberpunk Sunset",
    colors: ["#ec4899", "#f43f5e", "#fb7185", "#f97316", "#fb923c", "#f59e0b", "#8b5cf6", "#a855f7", "#d946ef", "#c026d3"],
  },
  monochrome: {
    name: "Monochrome Slate",
    colors: ["#334155", "#475569", "#64748b", "#94a3b8", "#cbd5e1", "#1e293b", "#0f172a", "#64748b", "#94a3b8", "#334155"],
  },
};

const PALETTE = PALETTES.indigo.colors;

const CHART_TYPES = [
  { id: "bar", label: "Bar", icon: "bar" },
  { id: "line", label: "Line / Time Series", icon: "line" },
  { id: "scatter", label: "Scatter", icon: "scatter" },
  { id: "pie", label: "Pie", icon: "pie" },
  { id: "doughnut", label: "Donut", icon: "donut" },
  { id: "boxplot", label: "Box Plot", icon: "box" },
  { id: "radar", label: "Radar / Spider", icon: "radar" },
  { id: "polarArea", label: "Polar Area", icon: "polar" },
  { id: "heatmap", label: "Correlation Matrix", icon: "heatmap" },
  { id: "waterfall", label: "Waterfall Bridge", icon: "waterfall" },
  { id: "funnel", label: "Conversion Funnel", icon: "funnel" },
  { id: "combo", label: "Dual-Axis Combo", icon: "combo" },
];

function fmtNum(v: number): string {
  if (Math.abs(v) >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (Math.abs(v) >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v % 1 === 0 ? String(v) : v.toFixed(2);
}

// -- Box Plot --
function BoxPlotViz({ data, formatted, xLabel = "Category", yLabel = "Value" }: { data: any; formatted: any; xLabel?: string; yLabel?: string }) {
  if (!data || typeof data.min !== "number") return (
    <p className="text-xs text-center py-10 font-medium" style={{ color: "var(--txt-m)" }}>Invalid data</p>
  );
  const range = data.max - data.min;
  const pad = range === 0 ? 1 : range * 0.12;
  const minX = data.min - pad;
  const total = (data.max + pad) - minX;
  const toPct = (v: number) => `${Math.max(0, Math.min(100, ((v - minX) / total) * 100)).toFixed(2)}%`;
  return (
    <div className="w-full h-full flex flex-col justify-center px-4 select-none">
      <div className="text-center mb-1 font-bold text-xs uppercase tracking-wider" style={{ color: "var(--txt)" }}>{toLabel(xLabel)} Distribution ({toLabel(yLabel)})</div>
      <div className="relative w-full h-14 flex items-center mb-8 mt-2">
        <div className="absolute h-0.5" style={{ left: toPct(data.min), right: `${(100 - parseFloat(toPct(data.max))).toFixed(2)}%`, background: "var(--border)" }} />
        <div className="absolute w-1 h-5 rounded" style={{ left: toPct(data.min), top: "50%", transform: "translate(-50%,-50%)", background: "var(--txt-m)" }} />
        <div className="absolute w-1 h-5 rounded" style={{ left: toPct(data.max), top: "50%", transform: "translate(-50%,-50%)", background: "var(--txt-m)" }} />
        <div className="absolute h-9 rounded-md" style={{ left: toPct(data.q1), width: `${((data.q3 - data.q1) / total) * 100}%`, background: "rgba(99,102,241,0.25)", border: "2px solid #6366f1", top: "50%", transform: "translateY(-50%)" }} />
        <div className="absolute w-1 h-10 rounded bg-amber-500 shadow-md" style={{ left: toPct(data.median), top: "50%", transform: "translate(-50%,-50%)" }} />
        <div className="absolute text-[10px] font-bold font-mono -bottom-6 text-center" style={{ left: toPct(data.min), transform: "translateX(-50%)", color: "var(--txt)" }}>{formatted?.min}</div>
        <div className="absolute text-[10px] font-bold font-mono -bottom-6 text-center" style={{ left: toPct(data.max), transform: "translateX(-50%)", color: "var(--txt)" }}>{formatted?.max}</div>
        <div className="absolute text-[11px] font-black font-mono -top-7 text-center text-amber-500" style={{ left: toPct(data.median), transform: "translateX(-50%)" }}>{formatted?.median}</div>
      </div>
      <div className="grid grid-cols-3 gap-2 mt-2">
        {([["Q1", formatted?.q1, "#4f46e5"], ["Median", formatted?.median, "#d97706"], ["Q3", formatted?.q3, "#4f46e5"]] as [string, string, string][]).map(([lbl, val, col]) => (
          <div key={lbl} className="text-center rounded-lg py-1.5 border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
            <p className="text-[9px] uppercase tracking-widest font-extrabold mb-0.5" style={{ color: "var(--txt-m)" }}>{lbl}</p>
            <p className="text-xs font-black font-mono" style={{ color: col }}>{val}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// -- KPI Card --
function KpiCard({ stat, idx }: { stat: any; idx: number }) {
  const color = stat.color || PALETTE[idx % PALETTE.length];
  const icon = stat.type === "entity_count" ? <Layers size={14} /> : stat.type === "distinct" ? <PieChart size={14} /> : stat.type === "completeness" ? <Activity size={14} /> : stat.type === "rows" ? <LayoutDashboard size={14} /> : <BarChart4 size={14} />;
  return (
    <div className="relative overflow-hidden rounded-2xl p-5 flex flex-col justify-between" style={{ background: "var(--surface)", border: "1px solid var(--border)", minHeight: 110 }}>
      <div className="absolute -top-8 -right-8 w-24 h-24 rounded-full opacity-15 blur-2xl pointer-events-none" style={{ background: color }} />
      <div className="flex items-start justify-between">
        <p className="text-[10px] font-bold uppercase tracking-widest truncate pr-2" style={{ color: "var(--txt-m)" }}>{stat.label}</p>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `${color}22`, color }}>
          {icon}
        </div>
      </div>
      <div>
        <p className="text-3xl font-black tracking-tight mt-2" style={{ color }}>{stat.value}</p>
        {stat.sub && <p className="text-[10px] font-semibold mt-1 truncate" style={{ color: "var(--txt-m)" }}>{stat.sub}</p>}
      </div>
    </div>
  );
}

// helpers
const toLabel = (s: string) => (s || "").replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase());

// -- Correlation Matrix Heatmap --
function HeatmapViz({ labels, values }: { labels: string[]; values: number[][] }) {
  if (!values || !Array.isArray(values) || !values.length) {
    return <p className="text-xs text-center py-10" style={{ color: "var(--txt-m)" }}>No correlation data</p>;
  }
  return (
    <div className="w-full h-full overflow-auto p-1 flex flex-col justify-center">
      <div className="grid gap-1 items-center" style={{ gridTemplateColumns: `70px repeat(${labels.length}, minmax(36px, 1fr))` }}>
        <div />
        {labels.map((col, j) => (
          <div key={`h-top-${j}`} className="text-[9px] font-bold truncate text-center" style={{ color: "var(--txt-m)" }} title={col}>
            {col.slice(0, 6)}
          </div>
        ))}
        {labels.map((rowCol, i) => (
          <React.Fragment key={`row-${i}`}>
            <div className="text-[9px] font-bold truncate text-right pr-2" style={{ color: "var(--txt-m)" }} title={rowCol}>
              {rowCol.slice(0, 8)}
            </div>
            {labels.map((_, j) => {
              const val = values[i]?.[j] ?? 0;
              const isPos = val >= 0;
              const abs = Math.min(1, Math.abs(val));
              const bg = isPos
                ? `rgba(99, 102, 241, ${abs * 0.85 + 0.1})`
                : `rgba(239, 68, 68, ${abs * 0.85 + 0.1})`;
              const textColor = abs > 0.45 ? "#ffffff" : "#1e293b";
              return (
                <div
                  key={`cell-${i}-${j}`}
                  className="rounded flex items-center justify-center text-[10px] font-mono font-bold transition-transform hover:scale-110 cursor-pointer shadow-xs"
                  style={{ height: 28, background: bg, color: textColor }}
                  title={`${rowCol} ✕ ${labels[j]}: ${val.toFixed(3)}`}
                >
                  {val.toFixed(2)}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

// -- Waterfall Bridge --
function WaterfallViz({ labels, values }: { labels: string[]; values: number[] }) {
  if (!values || !values.length) return <p className="text-xs text-center py-10" style={{ color: "var(--txt-m)" }}>No waterfall data</p>;
  const maxVal = Math.max(...values.map(Math.abs), 1);
  return (
    <div className="w-full h-full flex flex-col justify-end p-2">
      <div className="flex items-end justify-between gap-1.5 h-44 border-b pb-1" style={{ borderColor: "var(--border)" }}>
        {labels.map((label, i) => {
          const val = values[i] ?? 0;
          const isNet = i === labels.length - 1;
          const isPos = val >= 0;
          const heightPct = Math.max(8, Math.min(100, (Math.abs(val) / maxVal) * 90));
          const color = isNet ? "#6366f1" : isPos ? "#10b981" : "#ef4444";
          return (
            <div key={`wf-${i}`} className="flex-1 flex flex-col items-center justify-end h-full group">
              <span className="text-[8px] font-mono font-bold mb-0.5 opacity-90 group-hover:opacity-100" style={{ color: "var(--txt)" }}>
                {isPos && !isNet ? "+" : ""}{fmtNum(val)}
              </span>
              <div
                className="w-full rounded-t transition-all duration-300 group-hover:brightness-110 shadow-sm"
                style={{ height: `${heightPct}%`, background: color }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between gap-1 mt-1.5">
        {labels.map((label, i) => (
          <div key={`wf-lbl-${i}`} className="flex-1 text-[8px] font-bold truncate text-center" style={{ color: "var(--txt-m)" }} title={label}>
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}

// -- Conversion Funnel --
function FunnelViz({ labels, values }: { labels: string[]; values: any }) {
  const counts: number[] = Array.isArray(values) ? values : (values?.counts || []);
  const pcts: number[] = !Array.isArray(values) && values?.pcts ? values.pcts : counts.map((c: number) => counts[0] > 0 ? Math.round((c / counts[0]) * 100) : 100);
  if (!counts.length) return <p className="text-xs text-center py-10" style={{ color: "var(--txt-m)" }}>No funnel data</p>;
  return (
    <div className="w-full h-full flex flex-col justify-center gap-2.5 p-3">
      {labels.map((stage, i) => {
        const count = counts[i] ?? 0;
        const pct = pcts[i] ?? 100;
        return (
          <div key={`fn-${i}`} className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-bold" style={{ color: "var(--txt)" }}>
              <span className="truncate max-w-[180px]">{stage}</span>
              <span className="font-mono font-extrabold" style={{ color: "var(--accent)" }}>{fmtNum(count)} ({pct}%)</span>
            </div>
            <div className="w-full h-4 rounded-full overflow-hidden relative shadow-inner border" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${Math.max(6, Math.min(100, pct))}%`,
                  background: `linear-gradient(90deg, #6366f1, #8b5cf6)`,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// -- Chart renderer --
function renderChart(ch: any, idx: number, activePaletteColors: string[] = PALETTE) {
  const color = activePaletteColors[idx % activePaletteColors.length];
  const xLabel = toLabel(ch.x_col || "Category");
  const agg = ch.agg_type && ch.agg_type !== "none" ? ` (${ch.agg_type})` : "";
  const yLabel = toLabel(ch.y_col || "Count") + agg;

  const tooltip = {
    callbacks: {
      title: (items: any[]) => `${xLabel}: ${items[0]?.label ?? ""}`,
      label: (ctx: any) => {
        const v = ctx.parsed?.y ?? ctx.raw;
        if (typeof v === "number") return `  ${yLabel}: ${fmtNum(v)}`;
        if (v && typeof v.y === "number") return `  ${yLabel}: ${fmtNum(v.y)}`;
        return `  ${v}`;
      },
    },
    displayColors: false,
    backgroundColor: "rgba(8,8,18,0.97)",
    borderColor: "rgba(255,255,255,0.15)",
    borderWidth: 1,
    titleColor: "rgba(255,255,255,0.95)",
    bodyColor: "rgba(255,255,255,0.75)",
    padding: 12,
    cornerRadius: 10,
  };

  const scales: any = {
    x: {
      title: {
        display: true,
        text: xLabel,
        color: "#0f172a",
        font: { size: 12, weight: "bold", family: "inherit" },
        padding: { top: 6 },
      },
      ticks: {
        color: "#1e293b",
        font: { size: 11, weight: "bold" },
        maxTicksLimit: 10,
        maxRotation: 30,
        autoSkip: true,
      },
      grid: { color: "rgba(0,0,0,0.06)" },
      border: { color: "#94a3b8" },
    },
    y: {
      title: {
        display: true,
        text: yLabel,
        color: "#0f172a",
        font: { size: 12, weight: "bold", family: "inherit" },
        padding: { bottom: 6 },
      },
      ticks: {
        color: "#1e293b",
        font: { size: 11, weight: "bold" },
        callback: (v: any) => fmtNum(Number(v)),
        maxTicksLimit: 6,
      },
      grid: { color: "rgba(0,0,0,0.06)" },
      border: { color: "#94a3b8" },
      beginAtZero: true,
    },
  };

  const common: any = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 500 },
    layout: { padding: { top: 4, right: 10, bottom: 4, left: 4 } },
    plugins: { legend: { display: false }, tooltip },
    scales,
  };

  if (ch.type === "radar") {
    return <Radar
      data={{
        labels: ch.labels,
        datasets: [{
          label: yLabel,
          data: ch.values,
          backgroundColor: `${color}33`,
          borderColor: color,
          borderWidth: 2,
          pointBackgroundColor: color,
          pointBorderColor: "#fff",
          pointHoverRadius: 6,
        }],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip },
        scales: {
          r: {
            angleLines: { color: "rgba(0,0,0,0.1)" },
            grid: { color: "rgba(0,0,0,0.08)" },
            pointLabels: { color: "#0f172a", font: { size: 11, weight: "bold" } },
            ticks: { color: "#334155", backdropColor: "transparent", font: { size: 9 } },
          },
        },
      }}
    />;
  }

  if (ch.type === "polarArea") {
    return <PolarArea
      data={{
        labels: ch.labels,
        datasets: [{
          data: ch.values,
          backgroundColor: (ch.labels || []).map((_: any, i: number) => `${activePaletteColors[i % activePaletteColors.length]}bb`),
          borderColor: "rgba(0,0,0,0.25)",
          borderWidth: 1.5,
        }],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: true, position: "right" as const }, tooltip },
        scales: {
          r: {
            grid: { color: "rgba(0,0,0,0.08)" },
            ticks: { backdropColor: "transparent", color: "#334155", font: { size: 9 } },
          },
        },
      }}
    />;
  }

  if (ch.type === "heatmap") {
    return <HeatmapViz labels={ch.labels || []} values={ch.values || []} />;
  }

  if (ch.type === "waterfall") {
    return <WaterfallViz labels={ch.labels || []} values={ch.values || []} />;
  }

  if (ch.type === "funnel") {
    return <FunnelViz labels={ch.labels || []} values={ch.values} />;
  }

  if (ch.type === "combo") {
    const bars = ch.values?.bars || (Array.isArray(ch.values) ? ch.values : []);
    const lines = ch.values?.lines || [];
    return <Bar
      data={{
        labels: ch.labels,
        datasets: [
          {
            type: "bar" as const,
            label: `${yLabel} (Volume)`,
            data: bars,
            backgroundColor: (ch.labels || []).map((_: any, i: number) => `${activePaletteColors[i % activePaletteColors.length]}cc`),
            borderColor: (ch.labels || []).map((_: any, i: number) => activePaletteColors[i % activePaletteColors.length]),
            borderWidth: 1.5,
            borderRadius: 6,
            yAxisID: "y",
          },
          {
            type: "line" as const,
            label: `${yLabel} (Trend)`,
            data: lines,
            borderColor: "#f59e0b",
            backgroundColor: "rgba(245,158,11,0.1)",
            borderWidth: 2.5,
            tension: 0.35,
            pointRadius: 4,
            pointBackgroundColor: "#fff",
            pointBorderColor: "#f59e0b",
            pointBorderWidth: 2,
            yAxisID: "y1",
          },
        ] as any,
      }}
      options={{
        ...common,
        plugins: { legend: { display: true, position: "top" as const }, tooltip },
        scales: {
          ...scales,
          y1: {
            type: "linear" as const,
            display: true,
            position: "right" as const,
            grid: { drawOnChartArea: false },
            ticks: { color: "#d97706", font: { size: 10, weight: "bold" }, callback: (v: any) => fmtNum(Number(v)) },
          },
        },
      }}
    />;
  }

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
      data={{ labels: ch.labels, datasets: [{ data: ch.values, backgroundColor: activePaletteColors, borderColor: "rgba(0,0,0,0.3)", borderWidth: 2, hoverOffset: 12 }] }}
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
              color: "#0f172a",
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
                    fillStyle: activePaletteColors[i % activePaletteColors.length],
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

  // Bar / histogram
  return <Bar
    data={{
      labels: ch.labels,
      datasets: [{
        label: yLabel,
        data: ch.values,
        backgroundColor: (ch.labels || []).map((_: any, i: number) => `${activePaletteColors[i % activePaletteColors.length]}cc`),
        borderColor: (ch.labels || []).map((_: any, i: number) => activePaletteColors[i % activePaletteColors.length]),
        borderWidth: 1.5,
        borderRadius: 6,
        borderSkipped: false as const,
      }],
    }}
    options={{
      ...common,
      scales: {
        ...scales,
        x: {
          ...scales.x,
          ticks: {
            color: "#1e293b",
            font: { size: 11, weight: "bold" },
            maxRotation: 45,
            minRotation: 0,
            autoSkip: true,
            maxTicksLimit: 12,
          },
        },
      },
    }}
  />;
}

// -- Chart Card --
function ChartCard({
  ch,
  idx,
  onRemove,
  onTogglePin,
  isPinned,
  activePaletteColors,
}: {
  ch: any;
  idx: number;
  onRemove: () => void;
  onTogglePin?: () => void;
  isPinned?: boolean;
  activePaletteColors: string[];
}) {
  const cardRef = React.useRef<HTMLDivElement>(null);
  const color = activePaletteColors[idx % activePaletteColors.length];
  const numericVals = Array.isArray(ch.values) && ch.values.length > 0 && typeof ch.values[0] === "number" ? ch.values as number[] : null;
  const maxVal = numericVals ? Math.max(...numericVals) : null;
  const minVal = numericVals ? Math.min(...numericVals) : null;
  const totalPts = Array.isArray(ch.values) ? ch.values.length : 0;
  const isPie = ch.type === "pie" || ch.type === "doughnut";
  const chartH = isPie ? 300 : 280;

  const downloadPng = () => {
    const canvas = cardRef.current?.querySelector("canvas");
    if (canvas) {
      const url = canvas.toDataURL("image/png");
      const a = document.createElement("a");
      a.href = url;
      a.download = `${(ch.title || "chart").toLowerCase().replace(/\s+/g, "_")}.png`;
      a.click();
    }
  };

  return (
    <div ref={cardRef} className="rounded-2xl overflow-hidden flex flex-col" style={{ background: "var(--surface)", border: isPinned ? "1px solid rgba(245,158,11,0.4)" : "1px solid var(--border)", boxShadow: isPinned ? "0 4px 30px rgba(245,158,11,0.15)" : "0 4px 30px rgba(0,0,0,0.25)" }}>
      {/* Accent top bar */}
      <div className="h-[3px] w-full" style={{ background: isPinned ? "linear-gradient(90deg, #f59e0b, #fbbf24, #f59e0b)" : `linear-gradient(90deg,${color},${color}44)` }} />
      <div className="flex items-start justify-between px-5 pt-4 pb-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: isPinned ? "#f59e0b" : color, boxShadow: `0 0 5px ${isPinned ? "#f59e0b" : color}` }} />
            <p className="text-[11px] font-black uppercase tracking-wide truncate" style={{ color: "var(--txt)" }}>{ch.title}</p>
            {isPinned && (
              <span className="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30 flex items-center gap-0.5">
                <Pin size={8} className="fill-amber-400 text-amber-400" /> Pinned
              </span>
            )}
            {ch.is_custom && <span className="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full" style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1", border: "1px solid rgba(99,102,241,0.25)" }}>Custom</span>}
            {ch.agent_source && (
              <span className="text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded-full flex items-center gap-1" style={{ background: "rgba(16,185,129,0.12)", color: "#10b981", border: "1px solid rgba(16,185,129,0.25)" }}>
                <Bot size={9} /> {ch.agent_source}
              </span>
            )}
            <span
              className="text-[8px] font-mono uppercase tracking-widest px-1.5 py-0.5 rounded border"
              style={{ background: "var(--inp-bg)", color: "var(--txt-m)", borderColor: "var(--border)" }}
            >
              {ch.type}
            </span>
          </div>
          {/* Axis context */}
          {ch.x_col && (
            <p className="text-[9px] font-mono" style={{ color: "var(--txt-m)" }}>
              {ch.x_col}
              {ch.y_col && ch.y_col !== "count" && ch.y_col !== "distribution" ? ` → ${ch.y_col}` : ""}
              {ch.agg_type && ch.agg_type !== "none" && ch.y_col && ch.y_col !== "count"
                ? ` · ${ch.agg_type}`
                : (ch.agg_type === "count" || ch.y_col === "count" ? " · Count" : "")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1.5 ml-2">
          {onTogglePin && (
            <button
              onClick={onTogglePin}
              title={isPinned ? "Unpin chart" : "Pin chart to top (max 3)"}
              className={`flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center transition-all cursor-pointer ${
                isPinned ? "bg-amber-500/20 text-amber-400 border border-amber-500/40" : "opacity-70 hover:opacity-100 hover:bg-black/5 dark:hover:bg-white/10"
              }`}
              style={{ color: isPinned ? "#f59e0b" : "var(--txt)" }}
            >
              <Pin size={12} className={isPinned ? "fill-amber-400 text-amber-400" : ""} />
            </button>
          )}
          <button
            onClick={downloadPng}
            title="Export High-Res PNG"
            className="w-6 h-6 rounded-lg flex items-center justify-center transition-all cursor-pointer opacity-70 hover:opacity-100 hover:bg-black/5 dark:hover:bg-white/10"
            style={{ color: "var(--txt)" }}
          >
            <Download size={12} />
          </button>
          <button
            onClick={onRemove}
            title="Remove / dismiss chart"
            className="flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center transition-all cursor-pointer text-red-400 hover:bg-red-500/10"
          >
            <X size={12} />
          </button>
        </div>
      </div>
      {/* Stats ribbon */}
      {numericVals && ch.type !== "boxplot" && (
        <div className="flex items-center gap-3 px-5 pb-2">
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: "var(--inp-bg)", color: "var(--txt-m)" }}>{totalPts} pts</span>
          {maxVal !== null && <span className="text-[9px] font-bold" style={{ color: "#10b981" }}>↑ {fmtNum(maxVal)}</span>}
          {minVal !== null && <span className="text-[9px] font-bold" style={{ color: "#f59e0b" }}>↓ {fmtNum(minVal)}</span>}
          {maxVal !== null && minVal !== null && maxVal !== minVal && <span className="text-[9px] font-bold" style={{ color: "var(--txt-m)" }}>Δ {fmtNum(maxVal - minVal)}</span>}
        </div>
      )}
      {/* Chart area */}
      <div style={{ height: chartH, position: "relative", padding: "10px", background: "#ffffff", borderRadius: "12px", margin: "0 12px 12px", border: "1px solid #cbd5e1" }}>
        {ch.type === "boxplot"
          ? <BoxPlotViz data={ch.values} formatted={ch.formatted_values} xLabel={ch.x_col} yLabel={ch.y_col} />
          : renderChart(ch, idx, activePaletteColors)
        }
      </div>
    </div>
  );
}

// -- Main --
export function DashboardTab() {
  const { uploadId, profile } = useWorkspace();
  const [governedBy, setGovernedBy] = useState<string>("Unified Analytical Engine & Dynamic Visuals");
  const [isDashLoading, setIsDashLoading] = useState(false);
  const [dashStats, setDashStats] = useState<any[]>([]);
  const [dashCharts, setDashCharts] = useState<any[]>([]);
  const [dashSummary, setDashSummary] = useState("");
  const [dashIdStats, setDashIdStats] = useState<any>(null);
  const [dashNumericCols, setDashNumericCols] = useState<string[]>([]);
  const [validMetrics, setValidMetrics] = useState<string[]>([]);
  const [idCols, setIdCols] = useState<string[]>([]);
  const [catCols, setCatCols] = useState<string[]>([]);
  const [selectedMetric, setSelectedMetric] = useState<string>("");
  const [dashInsights, setDashInsights] = useState<any[]>([]);
  const [pinnedInsights, setPinnedInsights] = useState<any[]>([]);
  const [pinnedChartIds, setPinnedChartIds] = useState<string[]>([]);
  const [dismissedChartIds, setDismissedChartIds] = useState<string[]>([]);
  const [profileCols, setProfileCols] = useState<string[]>([]);
  const [builderOpen, setBuilderOpen] = useState(false);
  const [selectedPalette, setSelectedPalette] = useState<string>("indigo");
  const [customChart, setCustomChart] = useState({ id: null as any, chart_type: "bar", x_col: "", y_col: "", agg_type: "count", title: "", is_area: false, top_n: 10 });
  const [isGeneratingChart, setIsGeneratingChart] = useState(false);
  const [customChartError, setCustomChartError] = useState("");

  const activeColors = PALETTES[selectedPalette]?.colors || PALETTES.indigo.colors;

  // Load persisted pinned and dismissed charts
  useEffect(() => {
    if (uploadId) {
      try {
        const savedPinned = localStorage.getItem(`df_pinned_charts_${uploadId}`);
        if (savedPinned) setPinnedChartIds(JSON.parse(savedPinned));
        const savedDismissed = localStorage.getItem(`df_dismissed_charts_${uploadId}`);
        if (savedDismissed) setDismissedChartIds(JSON.parse(savedDismissed));
      } catch (err) {
        console.error("Failed loading saved chart preferences", err);
      }
    }
  }, [uploadId]);

  const loadDashboard = useCallback(async (metricOverride?: string) => {
    if (!uploadId) return;
    setIsDashLoading(true);
    const metricToUse = metricOverride !== undefined ? metricOverride : selectedMetric;
    try {
      const res = await apiFetch("/dashboard/agentic-auto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chart_dim: "", chart_metric: metricToUse, upload_id: uploadId }),
      });
      if (res.ok) {
        const d = await res.json();
        setDashStats(d.stats || []);
        setDashCharts(d.charts || []);
        setDashSummary(d.summary || "");
        setDashIdStats(d.id_stats || null);
        setDashNumericCols(d.numeric_cols || []);
        setValidMetrics(d.valid_metrics || []);
        setIdCols(d.id_cols || []);
        setCatCols(d.cat_cols || []);
        setDashInsights(d.insights || []);
        setPinnedInsights(d.pinned_insights || []);
        if (d.governed_by) setGovernedBy(d.governed_by);
        if (d.metric) {
          setSelectedMetric(d.metric);
        }
        setProfileCols(d.cat_cols ? [...(d.valid_metrics || []), ...(d.id_cols || []), ...(d.cat_cols || [])] : profile?.columns?.map((c: any) => c.name) || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsDashLoading(false);
    }
  }, [uploadId, profile, selectedMetric]);

  const handleMetricChange = (newMetric: string) => {
    setSelectedMetric(newMetric);
    loadDashboard(newMetric);
  };

  const unpinInsight = async (ins: any) => {
    if (!uploadId) return;
    const insId = ins.id || ins.title;
    try {
      const res = await apiFetch("/dashboard/pin-insight", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, insight: ins, action: "unpin" }),
      });
      if (res.ok) {
        setPinnedInsights(prev => prev.filter(p => (p.id || p.title) !== insId));
      }
    } catch (e) {
      console.error("Unpinning insight failed:", e);
    }
  };

  useEffect(() => {
    if (uploadId) loadDashboard();
  }, [uploadId, loadDashboard]);

  const saveCustomChart = async () => {
    setCustomChartError(""); setIsGeneratingChart(true);
    try {
      const isHeatmap = customChart.chart_type === "heatmap";
      const hasY = customChart.y_col && customChart.y_col.trim() !== "" && customChart.y_col !== "count";
      const effectiveAgg = !hasY ? "count" : (customChart.agg_type || "mean");

      const payload: any = {
        ...customChart,
        agg_type: effectiveAgg,
        upload_id: uploadId,
        x_col: customChart.x_col ? customChart.x_col.trim() : (isHeatmap ? "" : ""),
        y_col: hasY ? customChart.y_col.trim() : undefined,
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
      setCustomChart({ id: null, chart_type: "bar", x_col: "", y_col: "", agg_type: "count", title: "", is_area: false, top_n: 10 });
      setBuilderOpen(false);
      await loadDashboard();
    } catch (e: any) {
      setCustomChartError("Network error: " + (e.message || String(e)));
    } finally {
      setIsGeneratingChart(false);
    }
  };

  const getChartId = (c: any, index?: number) => {
    return String(c.id || c.title || `chart-${index}`);
  };

  const togglePinChart = (ch: any, index?: number) => {
    const cid = getChartId(ch, index);
    setPinnedChartIds(prev => {
      const isCurrentlyPinned = prev.includes(cid);
      if (isCurrentlyPinned) {
        const next = prev.filter(id => id !== cid);
        if (uploadId) {
          try { localStorage.setItem(`df_pinned_charts_${uploadId}`, JSON.stringify(next)); } catch {}
        }
        return next;
      }
      if (prev.length >= 3) {
        alert("Maximum 3 pinned charts allowed. Please unpin a chart first.");
        return prev;
      }
      const next = [...prev, cid];
      if (uploadId) {
        try { localStorage.setItem(`df_pinned_charts_${uploadId}`, JSON.stringify(next)); } catch {}
      }
      return next;
    });
  };

  const removeChart = async (ch: any, index?: number) => {
    const cid = getChartId(ch, index);
    if (ch.is_custom && ch.id) {
      try {
        await apiFetch("/dashboard/custom-chart/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ upload_id: uploadId, chart_id: ch.id }),
        });
      } catch (e) {
        console.error("Failed to delete custom chart:", e);
      }
    }
    // Dismiss from view and unpin if pinned
    setDismissedChartIds(prev => {
      const next = [...new Set([...prev, cid])];
      if (uploadId) {
        try { localStorage.setItem(`df_dismissed_charts_${uploadId}`, JSON.stringify(next)); } catch {}
      }
      return next;
    });
    setPinnedChartIds(prev => {
      const next = prev.filter(id => id !== cid);
      if (uploadId) {
        try { localStorage.setItem(`df_pinned_charts_${uploadId}`, JSON.stringify(next)); } catch {}
      }
      return next;
    });
    setDashCharts(prev => prev.filter((c, i) => getChartId(c, i) !== cid));
  };

  const sel: React.CSSProperties = { padding: "0.5rem 0.75rem", borderRadius: "0.6rem", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", color: "var(--txt)", fontSize: "11px", fontWeight: 600, width: "100%", outline: "none" };

  // Empty state
  if (!dashStats.length && !isDashLoading) return (
    <div className="tab-panel px-4 py-8 md:px-8 space-y-6">
      <div className="flex flex-col items-center justify-center gap-6 py-20 text-center">
        <div className="w-20 h-20 rounded-full flex items-center justify-center" style={{ background: "linear-gradient(135deg,rgba(99,102,241,0.15),rgba(99,102,241,0.04))", border: "1px solid rgba(99,102,241,0.2)" }}>
          <LayoutDashboard size={36} style={{ color: "#6366f1" }} />
        </div>
        <div>
          <p className="font-black text-lg mb-1" style={{ color: "var(--txt)" }}>Dashboard Ready to Generate</p>
          <p className="text-sm max-w-md" style={{ color: "var(--txt-m)" }}>Synthesize an executive KPI strip, Pareto distributions, trends, and dispersion boxplots directly from your active dataset.</p>
        </div>
        <button onClick={() => loadDashboard()} className="px-6 py-3 rounded-xl font-bold text-sm text-white flex items-center gap-2 cursor-pointer" style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>
          <Sparkles size={16} className="text-amber-300" /> Synthesize Executive Dashboard
        </button>
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
          <div className="flex items-center gap-2.5">
            <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>Executive Dashboard</h2>
          </div>

        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Primary KPI Attribute Selector */}
          {(validMetrics.length > 0 || idCols.length > 0 || catCols.length > 0 || profileCols.length > 0) && (
            <div
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] font-bold shadow-sm"
              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
              title="Select which attribute anchors the executive summary KPI"
            >
              <Target size={13} className="text-indigo-400 flex-shrink-0" />
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 mr-1">KPI Focus:</span>
              <select
                value={selectedMetric}
                onChange={e => handleMetricChange(e.target.value)}
                className="bg-transparent border-none outline-none cursor-pointer font-sans text-[11px] font-semibold max-w-[140px] truncate"
                style={{ color: "var(--txt)" }}
              >
                {validMetrics.length > 0 && (
                  <optgroup label="Quantitative Measures" style={{ background: "var(--surface)", color: "var(--txt)" }}>
                    {validMetrics.map(col => (
                      <option key={`m-${col}`} value={col} style={{ background: "var(--surface)", color: "var(--txt)" }}>
                        {col}
                      </option>
                    ))}
                  </optgroup>
                )}
                {idCols.length > 0 && (
                  <optgroup label="Identifiers (Entity Count)" style={{ background: "var(--surface)", color: "var(--txt-m)" }}>
                    {idCols.map(col => (
                      <option key={`id-${col}`} value={col} style={{ background: "var(--surface)", color: "var(--txt)" }}>
                        {col} (ID)
                      </option>
                    ))}
                  </optgroup>
                )}
                {catCols.length > 0 && (
                  <optgroup label="Categorical Cohorts" style={{ background: "var(--surface)", color: "var(--txt-m)" }}>
                    {catCols.map(col => (
                      <option key={`c-${col}`} value={col} style={{ background: "var(--surface)", color: "var(--txt)" }}>
                        {col}
                      </option>
                    ))}
                  </optgroup>
                )}
                {validMetrics.length === 0 && idCols.length === 0 && catCols.length === 0 && profileCols.map(col => (
                  <option key={`fb-${col}`} value={col} style={{ background: "var(--surface)", color: "var(--txt)" }}>
                    {col}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Palette / Theme Selector */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-[11px] font-bold"
            style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
          >
            <Palette size={13} style={{ color: "var(--accent)" }} />
            <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 mr-1">Theme:</span>
            <select
              value={selectedPalette}
              onChange={e => setSelectedPalette(e.target.value)}
              className="bg-transparent border-none outline-none cursor-pointer font-sans text-[11px] font-semibold"
              style={{ color: "var(--txt)" }}
            >
              {Object.entries(PALETTES).map(([key, pal]) => (
                <option key={key} value={key} style={{ background: "var(--surface)", color: "var(--txt)" }}>
                  {pal.name}
                </option>
              ))}
            </select>
          </div>

          {/* Add Chart Button */}
          <button
            onClick={() => setBuilderOpen(b => !b)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold border transition-all cursor-pointer"
            style={{
              borderColor: builderOpen ? "#6366f1" : "var(--border)",
              background: builderOpen ? "rgba(99,102,241,0.12)" : "var(--card)",
              color: builderOpen ? "#6366f1" : "var(--txt)"
            }}
          >
            <Plus size={13} className="text-indigo-400" />
            {builderOpen ? "Close Builder" : "Add Chart"}
          </button>

          {/* Refresh Button */}
          <button onClick={() => loadDashboard()} disabled={isDashLoading} className="bp flex items-center gap-1.5 cursor-pointer">
            {isDashLoading ? <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg> : <RefreshCw size={13} />}
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
        <div className="rounded-2xl p-5 flex items-center gap-6" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "rgba(245,158,11,0.1)" }}>
            <GitBranch size={16} style={{ color: "#f59e0b" }} />
          </div>
          <div>
            <p className="text-[10px] font-black uppercase tracking-widest mb-1" style={{ color: "var(--txt-m)" }}>Index Column — <span className="font-mono">{dashIdStats.col}</span></p>
            <div className="flex gap-6">
              {([["Unique", dashIdStats.total], ["Min", dashIdStats.min], ["Max", dashIdStats.max]] as [string, any][]).map(([l, v]) => (
                <div key={l}><p className="text-[9px] uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>{l}</p><p className="text-lg font-black" style={{ color: "#f59e0b" }}>{v}</p></div>
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
            {customChart.chart_type === "heatmap" ? (
              <div className="p-3.5 rounded-xl text-xs flex items-center gap-2.5" style={{ background: "rgba(99,102,241,0.08)", color: "#818cf8", border: "1px solid rgba(99,102,241,0.2)" }}>
                <span>⚡ <strong>Correlation Matrix Heatmap:</strong> Automatically computes pairwise correlation across all numeric metrics or rank association across categorical cohorts in your dataset.</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>X Axis / Category</label>
                  <select value={customChart.x_col} onChange={e => setCustomChart(c => ({ ...c, x_col: e.target.value }))} style={sel}>
                    <option value="">— Select Column —</option>
                    {profileCols.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                {!["histogram", "boxplot"].includes(customChart.chart_type) && (
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>
                      {customChart.chart_type === "scatter" ? "Y Axis (Metric)" : "Y Axis / Value"}
                    </label>
                    <select value={customChart.y_col} onChange={e => setCustomChart(c => ({ ...c, y_col: e.target.value }))} style={sel}>
                      {customChart.chart_type === "scatter" ? (
                        <option value="">— Select Y Column —</option>
                      ) : (
                        <option value="">— Count Rows —</option>
                      )}
                      {(dashNumericCols.length > 0 ? dashNumericCols : profileCols.filter(c => c !== customChart.x_col)).map(c => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                  </div>
                )}
                {!["histogram", "boxplot", "scatter"].includes(customChart.chart_type) && (
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Aggregation</label>
                    <select value={customChart.agg_type} onChange={e => setCustomChart(c => ({ ...c, agg_type: e.target.value }))} style={sel}>
                      <option value="count">Count of Records</option>
                      <option value="sum">Sum Total</option>
                      <option value="mean">Average (Mean)</option>
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
            )}
            <div className="flex gap-3 items-end flex-wrap">
              <div className="flex-1 space-y-1.5 min-w-[180px]">
                <label className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Chart Title (optional)</label>
                <input type="text" value={customChart.title} onChange={e => setCustomChart(c => ({ ...c, title: e.target.value }))} placeholder="Auto-generated if blank" style={{ ...sel, fontFamily: "inherit" }} />
              </div>
              <button onClick={saveCustomChart} disabled={isGeneratingChart || (!customChart.x_col && customChart.chart_type !== "heatmap")}
                className="px-5 py-2 rounded-xl font-bold text-sm text-white transition-all"
                style={(!customChart.x_col && customChart.chart_type !== "heatmap") || isGeneratingChart ? { background: "rgba(99,102,241,0.3)", cursor: "not-allowed" } : { background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.25)" }}>
                {isGeneratingChart ? "Saving…" : "Add to Dashboard"}
              </button>
            </div>
            {customChartError && <p className="text-[11px] font-medium text-red-400">{customChartError}</p>}
          </div>
        </div>
      )}

      {/* Time Series & Advanced Forecast Section */}
      {dashInsights
        .filter((ins: any) => ins.type === "forecast" && !dismissedChartIds.includes(getChartId(ins)))
        .map((ins: any, i: number) => {
          const fcId = getChartId(ins, i);
          const isFcPinned = pinnedChartIds.includes(fcId);
          return (
            <div key={`dash-fc-${i}`} className="w-full">
              <ForecastCard
                ins={ins}
                isPinned={isFcPinned}
                onTogglePin={() => togglePinChart(ins, i)}
                onDismiss={() => removeChart(ins, i)}
              />
            </div>
          );
        })}

      {/* Pinned Strategic Findings from Insight Engine (Section 5.3 Pin Bridge) */}
      {pinnedInsights.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
              <h3 className="text-xs font-black uppercase tracking-wider text-amber-400">
                📌 Pinned Strategic Findings ({pinnedInsights.length})
              </h3>
            </div>
            <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>Curated from Insight Engine · Live Evaluated</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {pinnedInsights.map((ins, i) => (
              <InsightCard
                key={ins.id || `pinned-${i}`}
                ins={ins}
                idx={i}
                isPinned={true}
                onTogglePin={() => unpinInsight(ins)}
                onDismiss={() => unpinInsight(ins)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Charts Grid */}
      {(() => {
        const visibleCharts = dashCharts.filter((ch, i) => !dismissedChartIds.includes(getChartId(ch, i)));
        const sortedCharts = [...visibleCharts].sort((a, b) => {
          const aPinned = pinnedChartIds.includes(getChartId(a));
          const bPinned = pinnedChartIds.includes(getChartId(b));
          if (aPinned && !bPinned) return -1;
          if (!aPinned && bPinned) return 1;
          return 0;
        });

        if (sortedCharts.length === 0) return null;

        return (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {sortedCharts.map((ch, i) => {
              const cid = getChartId(ch, i);
              const isPinned = pinnedChartIds.includes(cid);
              return (
                <ChartCard
                  key={cid || `c-${i}`}
                  ch={ch}
                  idx={i}
                  isPinned={isPinned}
                  onTogglePin={() => togglePinChart(ch, i)}
                  onRemove={() => removeChart(ch, i)}
                  activePaletteColors={activeColors}
                />
              );
            })}
          </div>
        );
      })()}
    </div>
  );
}
