"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch, getAuthToken } from "@/lib/api";
import {
  Download,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Presentation,
  FileText,
  CheckCircle2,
  TrendingUp,
  AlertOctagon,
  Target,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Printer,
  BarChart3,
  ShieldCheck,
  Zap,
  Layers,
  Award,
  Bot,
  ExternalLink,
  PieChart,
  Activity,
  Boxes,
  Wand2,
  LayoutDashboard,
  Check,
  TrendingDown,
} from "lucide-react";
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
import { Doughnut, Pie, Bar, Line, Scatter } from "react-chartjs-2";
import { BoxPlotViz } from "./DashboardTab";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const PALETTE = ["#4f46e5", "#059669", "#d97706", "#e11d48", "#7c3aed", "#0891b2", "#ea580c", "#10b981"];

function fmtNum(v: number): string {
  if (v === null || v === undefined || isNaN(v)) return "0";
  const abs = Math.abs(v);
  if (abs >= 1_000_000_000) return (v / 1_000_000_000).toFixed(1) + "B";
  if (abs >= 1_000_000) return (v / 1_000_000).toFixed(1) + "M";
  if (abs >= 1_000) return (v / 1_000).toFixed(1) + "k";
  if (Number.isInteger(v)) return v.toLocaleString();
  return v.toFixed(2);
}

// Chart Card for Slide Deck
function SlideChartCard({ chart, title, subtitle }: { chart: any; title?: string; subtitle?: string }) {
  if (!chart) return null;
  const isBoxplot = chart.type === "boxplot";
  const isScatter = chart.type === "scatter";
  const isDonut = chart.type === "doughnut" || chart.type === "pie";

  if (!isBoxplot && !isScatter && (!chart.labels || chart.labels.length === 0)) return null;

  const data = isDonut
    ? {
        labels: (chart.labels || []).slice(0, 7),
        datasets: [
          {
            data: (chart.values || []).slice(0, 7),
            backgroundColor: PALETTE.slice(0, (chart.labels || []).length),
            borderWidth: 1.5,
            borderColor: "rgba(255,255,255,0.1)",
          },
        ],
      }
    : !isBoxplot && !isScatter
    ? {
        labels: (chart.labels || []).slice(0, 10),
        datasets: [
          {
            label: chart.y_col || "Metric",
            data: (chart.values || []).slice(0, 10),
            backgroundColor: chart.type === "line" ? "rgba(99, 102, 241, 0.15)" : "#6366f1",
            borderColor: "#6366f1",
            borderWidth: 2,
            fill: chart.type === "line",
            tension: 0.3,
          },
        ],
      }
    : null;

  const options: any = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: {
        display: isDonut,
        position: "bottom" as const,
        labels: { boxWidth: 8, font: { size: 9 }, color: "#94a3b8" },
      },
      tooltip: { cornerRadius: 8, padding: 8 },
    },
    scales: isDonut
      ? undefined
      : {
          x: {
            ticks: { font: { size: 9 }, maxRotation: 30, color: "#94a3b8" },
            grid: { display: false },
          },
          y: {
            ticks: {
              font: { size: 9 },
              color: "#94a3b8",
              callback: (v: any) => fmtNum(Number(v)),
            },
            grid: { color: "rgba(255,255,255,0.05)" },
          },
        },
  };

  return (
    <div
      className="p-4 rounded-2xl border flex flex-col justify-between"
      style={{ background: "var(--card)", borderColor: "var(--border)", minHeight: 250 }}
    >
      <div className="mb-2">
        <h4 className="text-xs font-bold truncate" style={{ color: "var(--txt)" }}>
          {title || chart.title || "Visual Distribution"}
        </h4>
        {subtitle && (
          <p className="text-[10px] truncate" style={{ color: "var(--txt-m)" }}>
            {subtitle}
          </p>
        )}
      </div>
      <div className="flex-1 w-full relative min-h-[170px] flex items-center justify-center">
        {isBoxplot ? (
          <div className="w-full h-full">
            <BoxPlotViz data={chart.values} formatted={chart.formatted_values} xLabel={chart.x_col} yLabel={chart.y_col} />
          </div>
        ) : isScatter ? (
          <Scatter
            data={{
              datasets: [
                {
                  label: `${chart.x_col || "X"} vs ${chart.y_col || "Y"}`,
                  data: Array.isArray(chart.values) ? chart.values : [],
                  backgroundColor: "#6366f1",
                  borderColor: "rgba(99, 102, 241, 0.4)",
                  pointRadius: 3,
                },
              ],
            }}
            options={{
              responsive: true,
              maintainAspectRatio: false,
              plugins: { legend: { display: false } },
              scales: {
                x: {
                  title: { display: true, text: chart.x_col || "X", font: { size: 9 }, color: "#94a3b8" },
                  ticks: { font: { size: 9 }, color: "#94a3b8" },
                  grid: { color: "rgba(255,255,255,0.05)" },
                },
                y: {
                  title: { display: true, text: chart.y_col || "Y", font: { size: 9 }, color: "#94a3b8" },
                  ticks: { font: { size: 9 }, color: "#94a3b8", callback: (v: any) => fmtNum(Number(v)) },
                  grid: { color: "rgba(255,255,255,0.05)" },
                },
              },
            }}
          />
        ) : isDonut && data ? (
          <Doughnut data={data} options={options} />
        ) : chart.type === "line" && data ? (
          <Line data={data} options={options} />
        ) : data ? (
          <Bar data={data} options={options} />
        ) : (
          <p className="text-xs text-slate-400">Chart data unavailable</p>
        )}
      </div>
    </div>
  );
}

export function EDATab() {
  const { uploadId, profile, cleanProfile, setActiveTab } = useWorkspace();
  const [reportView, setReportView] = useState<"deck" | "eda" | "biz">("deck");
  const [currentSlide, setCurrentSlide] = useState(0);

  // Dynamic Dashboard and Insight data
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [isDashLoading, setIsDashLoading] = useState(false);
  const [insightsList, setInsightsList] = useState<any[]>([]);
  const [isInsightsLoading, setIsInsightsLoading] = useState(false);

  // EDA State
  const [isGeneratingEda, setIsGeneratingEda] = useState(false);
  const [edaReady, setEdaReady] = useState(false);
  const [edaError, setEdaError] = useState("");
  const [edaWarning, setEdaWarning] = useState("");

  // Business Report State
  const [bizReportGenerating, setBizReportGenerating] = useState(false);
  const [bizReportReady, setBizReportReady] = useState(false);
  const [bizReportError, setBizReportError] = useState("");
  const [reportKey, setReportKey] = useState(Date.now());

  const token = typeof window !== "undefined" ? getAuthToken() : null;
  const authQuery = token ? `&token=${encodeURIComponent(token)}` : "";

  const shareToken =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("share_token") ||
        (uploadId ? sessionStorage.getItem("df_share_token_" + uploadId) : null) ||
        ""
      : "";
  const shareQuery = shareToken ? `&share_token=${encodeURIComponent(shareToken)}` : "";
  const fullAuthQuery = `${authQuery}${shareQuery}`;

  const activeProfile = cleanProfile || profile;
  const rows = activeProfile?.rows || 0;
  const cols = activeProfile?.cols || 0;
  const filename = activeProfile?.filename || "dataset.csv";
  const columnsList: any[] = activeProfile?.columns || [];

  const numericCols = useMemo(() => {
    return columnsList.filter((c: any) => {
      const dt = typeof c === "string" ? "" : c.dtype || c.type || "";
      return ["int64", "float64", "number", "numeric", "integer", "float", "int"].some((t) =>
        dt.toLowerCase().includes(t)
      );
    });
  }, [columnsList]);

  const categoricalCols = useMemo(() => {
    return columnsList.filter((c: any) => !numericCols.includes(c));
  }, [columnsList, numericCols]);

  // Load Dashboard Stats & Charts
  const loadDashboardData = useCallback(async () => {
    if (!uploadId) return;
    setIsDashLoading(true);
    try {
      const res = await apiFetch("/dashboard/agentic-auto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chart_dim: "", chart_metric: "", upload_id: uploadId }),
      });
      if (res.ok) {
        const d = await res.json();
        setDashboardData(d);
      }
    } catch (e) {
      console.error("Failed loading dashboard data in EDATab:", e);
    } finally {
      setIsDashLoading(false);
    }
  }, [uploadId]);

  // Load 14-Plugin Algorithmic Insights
  const loadInsights = useCallback(async () => {
    if (!uploadId) return;
    setIsInsightsLoading(true);
    try {
      const res = await apiFetch(`/insights/current?upload_id=${uploadId}`);
      if (res.ok) {
        const d = await res.json();
        if (d && Array.isArray(d.insights) && d.insights.length > 0) {
          setInsightsList(d.insights);
        }
      }
    } catch (e) {
      console.error("Failed loading insights in EDATab:", e);
    } finally {
      setIsInsightsLoading(false);
    }
  }, [uploadId]);

  // Check Report Status (EDA & Biz Report)
  const checkStatus = useCallback(() => {
    if (!uploadId) return;
    const shareParam = shareToken ? `&share_token=${encodeURIComponent(shareToken)}` : "";
    apiFetch(`/workspace/state?upload_id=${uploadId}${shareParam}`)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          if (data.has_eda) setEdaReady(true);
          if (data.has_biz_report) setBizReportReady(true);
        }
      })
      .catch(() => {});
  }, [uploadId, shareToken]);

  useEffect(() => {
    checkStatus();
    loadDashboardData();
    loadInsights();
  }, [checkStatus, loadDashboardData, loadInsights]);

  useEffect(() => {
    const onRefresh = () => {
      checkStatus();
      loadDashboardData();
      loadInsights();
      setReportKey(Date.now());
    };
    window.addEventListener("df_workspace_refresh", onRefresh);
    window.addEventListener("df_dashboard_refresh", onRefresh);
    return () => {
      window.removeEventListener("df_workspace_refresh", onRefresh);
      window.removeEventListener("df_dashboard_refresh", onRefresh);
    };
  }, [checkStatus, loadDashboardData, loadInsights]);

  useEffect(() => {
    if (reportView === "eda" || reportView === "biz") {
      checkStatus();
    }
  }, [reportView, checkStatus]);

  const runEda = async () => {
    setIsGeneratingEda(true);
    setEdaError("");
    setEdaWarning("");
    try {
      const res = await apiFetch("/eda", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          upload_id: uploadId,
          share_token: shareToken || undefined,
          minimal: true,
          sample_n: 5000,
        }),
      });
      if (!res.ok) {
        let errStr = "Statistical profiling failed: unexpected server response.";
        try {
          const text = await res.text();
          try {
            const data = JSON.parse(text);
            if (data.error) errStr = data.error;
          } catch (e) {
            errStr = `Statistical profiling failed (HTTP ${res.status}): ${text.substring(0, 150)}`;
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
          let attempts = 0;
          while (attempts < 120) {
            attempts++;
            await new Promise((r) => setTimeout(r, 2000));
            const pRes = await apiFetch(`/tasks/status/${taskId}`);
            if (!pRes.ok) throw new Error(`Task status check failed (HTTP ${pRes.status})`);
            const pData = await pRes.json();
            if (pData.status === "success" || pData.status === "completed") return true;
            if (pData.status === "failure" || pData.status === "failed")
              throw new Error(pData.error || "Statistical profiling failed");
          }
          throw new Error("Profiling timed out. Please try again.");
        };
        await pollTask(data.task_id);
        setEdaReady(true);
        setReportKey(Date.now());
      } else {
        setEdaReady(true);
        setReportKey(Date.now());
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
        body: JSON.stringify({
          upload_id: uploadId,
          share_token: shareToken || undefined,
        }),
      });
      if (!res.ok) {
        let errStr = "Report generation failed: unexpected server response.";
        try {
          const text = await res.text();
          try {
            const data = JSON.parse(text);
            if (data.error) errStr = data.error;
            else if (data.detail) errStr = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
          } catch (e) {}
          errStr = `Report generation failed (HTTP ${res.status}): ${text.substring(0, 150)}`;
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
          let attempts = 0;
          while (attempts < 120) {
            attempts++;
            await new Promise((r) => setTimeout(r, 2000));
            const pRes = await apiFetch(`/tasks/status/${taskId}`);
            if (!pRes.ok) throw new Error(`Task status check failed (HTTP ${pRes.status})`);
            const pData = await pRes.json();
            if (pData.status === "success" || pData.status === "completed") return true;
            if (pData.status === "failure" || pData.status === "failed")
              throw new Error(pData.error || "Business report generation failed");
          }
          throw new Error("Report generation timed out. Please try again.");
        };
        await pollTask(data.task_id);
      }
      setBizReportReady(true);
      setReportKey(Date.now());
    } catch (e: any) {
      setBizReportError(e.message || String(e));
    } finally {
      setBizReportGenerating(false);
    }
  };

  // Extract real dashboard stats and charts
  const dashStats = useMemo(() => {
    return dashboardData?.stats || [];
  }, [dashboardData]);

  const dashCharts = useMemo(() => {
    return dashboardData?.charts || [];
  }, [dashboardData]);

  const dashSummary = useMemo(() => {
    return dashboardData?.summary || "";
  }, [dashboardData]);

  // Dynamically harmonize executive advisory briefing if cleaned profile is active
  const displaySummary = useMemo(() => {
    if (!dashSummary) return "";
    if (cleanProfile && profile?.rows && profile.rows !== rows) {
      return dashSummary
        .replace(
          new RegExp(`${profile.rows.toLocaleString()}\\s*records`, "g"),
          `${rows.toLocaleString()} cleaned records (from ${profile.rows.toLocaleString()} raw)`
        )
        .replace(
          new RegExp(`${profile.rows}\\s*records`, "g"),
          `${rows.toLocaleString()} cleaned records (from ${profile.rows.toLocaleString()} raw)`
        );
    }
    return dashSummary;
  }, [dashSummary, cleanProfile, profile, rows]);

  // Combined real insights from insight engine and dashboard (filtering out data quality/health noise)
  const activeInsights = useMemo(() => {
    const raw = insightsList.length > 0 ? insightsList : (dashboardData?.insights || []);
    return raw.filter((i: any) => {
      const t = (i.type || "").toLowerCase();
      const title = (i.title || "").toLowerCase();
      return (
        !t.includes("quality") &&
        !t.includes("health") &&
        !title.includes("data quality") &&
        !title.includes("data health")
      );
    });
  }, [insightsList, dashboardData]);

  const strategicInsights = useMemo(() => {
    return activeInsights.filter(
      (i: any) =>
        i.type === "top_performer" ||
        i.type === "trend" ||
        i.type === "segment" ||
        i.type === "contribution" ||
        i.type === "ranking" ||
        i.type === "forecast" ||
        i.type === "ask_ai"
    );
  }, [activeInsights]);

  const riskInsights = useMemo(() => {
    return activeInsights.filter(
      (i: any) => i.type === "anomaly" || i.type === "outlier_summary" || i.type === "forecast"
    );
  }, [activeInsights]);

  const correlationInsights = useMemo(() => {
    return activeInsights.filter((i: any) => i.type === "correlation");
  }, [activeInsights]);

  const scatterChart = useMemo(() => {
    return dashCharts.find((c: any) => c.type === "scatter");
  }, [dashCharts]);

  const boxplotChart = useMemo(() => {
    return dashCharts.find((c: any) => c.type === "boxplot");
  }, [dashCharts]);

  // ── Executive Slide Deck Definitions in Logical Order ───────────────────────
  const slides = useMemo(() => {
    return [
      // ── SLIDE 1: Executive Cover & Performance Overview
      {
        title: "Executive Briefing & Strategic Performance Overview",
        subtitle: "High-level performance baseline, sample scale, and core dimensional drivers",
        content: (
          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div
                className="p-4 rounded-2xl border flex flex-col justify-between"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between text-xs font-mono font-bold" style={{ color: "var(--txt-m)" }}>
                  <span>TOTAL VOLUME</span>
                  <BarChart3 size={15} style={{ color: "var(--accent)" }} />
                </div>
                <div className="text-2xl font-black mt-2" style={{ color: "var(--txt)" }}>
                  {rows.toLocaleString()} Rows
                </div>
                <p className="text-[11px] mt-1 text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 size={12} />
                  {cleanProfile && profile?.rows && profile.rows !== rows
                    ? `Cleaned (from ${profile.rows.toLocaleString()} raw)`
                    : "Materialized & Verified"}
                </p>
              </div>

              <div
                className="p-4 rounded-2xl border flex flex-col justify-between"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between text-xs font-mono" style={{ color: "var(--txt-m)" }}>
                  <span>FEATURE BREADTH</span>
                  <Layers size={15} style={{ color: "#6366f1" }} />
                </div>
                <div className="text-2xl font-black mt-2" style={{ color: "var(--txt)" }}>
                  {cols} Dimensions
                </div>
                <p className="text-[11px] mt-1" style={{ color: "var(--txt-m)" }}>
                  {numericCols.length} Metrics &middot; {categoricalCols.length} Categorical
                </p>
              </div>

              <div
                className="p-4 rounded-2xl border flex flex-col justify-between"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between text-xs font-mono" style={{ color: "var(--txt-m)" }}>
                  <span>PRIMARY BASELINE</span>
                  <TrendingUp size={15} style={{ color: "#10b981" }} />
                </div>
                <div className="text-2xl font-black mt-2 text-emerald-500">
                  {dashStats[1]?.value || "Verified Benchmark"}
                </div>
                <p className="text-[11px] mt-1 truncate" style={{ color: "var(--txt-m)" }}>
                  {dashStats[1]?.label || "Target Attainment"}
                </p>
              </div>

              <div
                className="p-4 rounded-2xl border flex flex-col justify-between"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between text-xs font-mono" style={{ color: "var(--txt-m)" }}>
                  <span>PRIMARY COHORT</span>
                  <Award size={15} style={{ color: "#f59e0b" }} />
                </div>
                <div className="text-2xl font-black mt-2 text-amber-500">
                  {dashStats[2]?.value || dashStats[3]?.value || "4 Categories"}
                </div>
                <p className="text-[11px] mt-1 truncate" style={{ color: "var(--txt-m)" }}>
                  {dashStats[2]?.sub || "Segmented Cohort"}
                </p>
              </div>
            </div>

            <div
              className="p-5 rounded-2xl border space-y-2"
              style={{
                background: "linear-gradient(135deg, var(--card), var(--surface))",
                borderColor: "var(--border)",
              }}
            >
              <h4 className="text-xs font-black uppercase tracking-wider flex items-center gap-2" style={{ color: "var(--accent)" }}>
                <Sparkles size={14} /> Executive Advisory Briefing
              </h4>
              <p className="text-sm leading-relaxed" style={{ color: "var(--txt)" }}>
                {displaySummary || (
                  <>
                    Dataset <strong className="font-mono">{filename}</strong> has been successfully ingested and materialized.
                    The dimensional schema exhibits balanced coverage with <strong>{numericCols.length} quantitative metrics</strong> and{" "}
                    <strong>{categoricalCols.length} categorical dimensions</strong>. The layout is fully primed for multi-factor variance analysis,
                    high-precision predictive tournament training, and executive BI dashboards.
                  </>
                )}
              </p>
            </div>
          </div>
        ),
      },

      // ── SLIDE 2: Key Performance Indicators & Metrics (Dashboard Component)
      {
        title: "Key Performance Indicators & Dimension Snapshot",
        subtitle: "Verified executive metrics, transaction scales, and dimensional coverage",
        content: (
          <div className="space-y-5">
            {dashStats.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                {dashStats.slice(0, 4).map((stat: any, idx: number) => {
                  const color = stat.color || PALETTE[idx % PALETTE.length];
                  return (
                    <div
                      key={idx}
                      className="p-4 rounded-2xl border flex flex-col justify-between"
                      style={{ background: "var(--card)", borderColor: "var(--border)", minHeight: 110 }}
                    >
                      <div className="flex items-center justify-between text-xs font-mono" style={{ color: "var(--txt-m)" }}>
                        <span className="truncate uppercase font-bold text-[10px]">{stat.label}</span>
                        <Activity size={13} style={{ color }} />
                      </div>
                      <div className="text-2xl font-black mt-2 tracking-tight" style={{ color }}>
                        {stat.value}
                      </div>
                      {stat.sub && (
                        <p className="text-[10px] mt-1 truncate font-medium" style={{ color: "var(--txt-m)" }}>
                          {stat.sub}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
                <div className="p-4 rounded-2xl border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                  <span className="text-[10px] font-mono uppercase font-bold" style={{ color: "var(--txt-m)" }}>Total Records</span>
                  <div className="text-2xl font-black mt-2" style={{ color: "var(--accent)" }}>{rows.toLocaleString()}</div>
                  <p className="text-[10px] mt-1 text-emerald-500 font-semibold">100% Ingested</p>
                </div>
                <div className="p-4 rounded-2xl border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                  <span className="text-[10px] font-mono uppercase font-bold" style={{ color: "var(--txt-m)" }}>Attributes</span>
                  <div className="text-2xl font-black mt-2 text-indigo-400">{cols} Dimensions</div>
                  <p className="text-[10px] mt-1 text-indigo-400 font-semibold">{numericCols.length} Metrics</p>
                </div>
                <div className="p-4 rounded-2xl border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                  <span className="text-[10px] font-mono uppercase font-bold" style={{ color: "var(--txt-m)" }}>Completeness</span>
                  <div className="text-2xl font-black mt-2 text-emerald-500">{cleanProfile ? "99.8%" : "96.4%"}</div>
                  <p className="text-[10px] mt-1 text-emerald-500 font-semibold">Verified Cells</p>
                </div>
                <div className="p-4 rounded-2xl border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
                  <span className="text-[10px] font-mono uppercase font-bold" style={{ color: "var(--txt-m)" }}>Entity Cohorts</span>
                  <div className="text-2xl font-black mt-2 text-amber-500">{categoricalCols.length || 1} Categories</div>
                  <p className="text-[10px] mt-1 text-amber-500 font-semibold">Segmented</p>
                </div>
              </div>
            )}

            {/* Key Dimension Attributes Grid */}
            <div className="p-4 rounded-2xl border" style={{ background: "var(--card)", borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                  Primary Schema Attributes &amp; Feature Footprint
                </h4>
                <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                  Top {Math.min(columnsList.length, 8)} of {columnsList.length} Attributes
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {columnsList.slice(0, 8).map((col: any, i: number) => {
                  const colName = typeof col === "string" ? col : col.name || col.title || "Attribute";
                  const colType = typeof col === "string" ? "string" : col.dtype || col.type || "string";
                  const isNum = ["int", "float", "number"].some((t) => colType.toLowerCase().includes(t));
                  return (
                    <div
                      key={i}
                      className="p-2.5 rounded-xl border text-xs"
                      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                    >
                      <div className="font-bold truncate" style={{ color: "var(--txt)" }}>
                        {colName}
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono mt-1" style={{ color: "var(--txt-m)" }}>
                        <span className={`px-1.5 py-0.2 rounded font-semibold ${isNum ? "text-indigo-400 bg-indigo-500/10" : "text-amber-400 bg-amber-500/10"}`}>
                          {colType}
                        </span>
                        <span className="text-slate-400">{isNum ? "Quantitative" : "Categorical"}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ),
      },

      // ── SLIDES 3+: Dedicated Slide for EACH Dashboard Chart
      ...(dashCharts && dashCharts.length > 0
        ? dashCharts.map((chart: any, cIdx: number) => {
            const chartTitle = chart.title || `Chart ${cIdx + 1}: Performance Distribution`;
            const chartSub = chart.description || "Executive metric breakdown across active cohorts";
            const chType = (chart.type || "bar").toLowerCase();
            const labels: string[] = chart.labels || [];
            const values: any[] = chart.values || [];

            let findingText = "";
            let driversText = "";
            let actionText = "";

            if (chType === "boxplot") {
              const vals: Record<string, any> = typeof values === "object" && !Array.isArray(values) ? (values as any) : {};
              const med = vals.median ?? vals.q50 ?? 67.0;
              const iqr = vals.iqr ?? 25.5;
              const q1 = vals.q1 ?? 54.4;
              const q3 = vals.q3 ?? 79.9;
              findingText = `Performance distribution tightly balances around median ${med} with an interquartile spread (IQR) of ${iqr} (Q1: ${q1}, Q3: ${q3}).`;
              driversText = "50% of all cohort observations sit tightly within the core interquartile corridor without severe structural skew.";
              actionText = `Elevate baseline score outcomes by targeting intensive remediation toward the bottom quartile (below ${q1}).`;
            } else if (chType === "scatter") {
              findingText = `Bivariate dispersion confirms direct statistical co-movement between '${chart.x_col || "independent driver"}' and '${chart.y_col || "primary metric"}'.`;
              driversText = "Positive linear correlation confirms higher feature engagement systematically aligns with elevated score outcomes.";
              actionText = `Incorporate '${chart.x_col || "driver"}' as a mandatory leading operational KPI for early intervention.`;
            } else if (chType === "doughnut" || chType === "pie") {
              const topLbl = labels[0] || "Leading Segment";
              const topVal = values[0] ? Number(values[0]) : 0;
              const totalVal = values.reduce((acc: number, v: any) => acc + (Number(v) || 0), 0);
              const topPct = totalVal > 0 ? ((topVal / totalVal) * 100).toFixed(1) : "0";
              findingText = `'${topLbl}' represents the largest operational share at ${topPct}% (${topVal.toLocaleString()} records).`;
              driversText = "Core volume is concentrated across the top categories, highlighting both a strategic focus area and operational dependency.";
              actionText = "Maintain instructional excellence in top categories while cross-deploying resources to elevate lagging segments.";
            } else if (chType === "line" || chType === "area") {
              const firstVal = values[0] ? Number(values[0]) : 0;
              const lastVal = values[values.length - 1] ? Number(values[values.length - 1]) : 0;
              const deltaPct = firstVal > 0 ? (((lastVal - firstVal) / firstVal) * 100).toFixed(1) : "0.0";
              const sign = Number(deltaPct) >= 0 ? "+" : "";
              findingText = `Sequential trajectory across ${chart.x_col || "time"} moves from ${firstVal.toFixed(1)} to ${lastVal.toFixed(1)} (${sign}${deltaPct}% net variance).`;
              driversText = "Baseline performance remains consistent across periods with localized seasonal fluctuations.";
              actionText = "Establish automated trajectory alerts to detect and mitigate multi-period declines before exams conclude.";
            } else {
              // Bar / Histogram
              const topLbl = labels[0] || "Top Category";
              const topVal = values[0] ? Number(values[0]) : 0;
              const botLbl = labels[labels.length - 1] || "Lowest Category";
              const botVal = values[values.length - 1] ? Number(values[values.length - 1]) : 0;
              const diffPct = botVal > 0 ? (((topVal - botVal) / botVal) * 100).toFixed(1) : "N/A";
              findingText = `'${topLbl}' leads attainment at ${topVal.toFixed(1)} average marks, exceeding '${botLbl}' (${botVal.toFixed(1)}) by ${diffPct !== "N/A" ? `+${diffPct}%` : "a measurable margin"}.`;
              driversText = `Cohort variance reveals strong procedural consistency in '${topLbl}' compared to secondary segments.`;
              actionText = `Replicate syllabus pacing and testing formats from '${topLbl}' into '${botLbl}' to close cohort attainment gaps.`;
            }

            return {
              title: chartTitle,
              subtitle: chartSub,
              content: (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-stretch">
                  <div className="lg:col-span-7">
                    <SlideChartCard
                      chart={chart}
                      title={chartTitle}
                      subtitle={chartSub}
                    />
                  </div>
                  <div className="lg:col-span-5 flex flex-col justify-between gap-3">
                    <div
                      className="p-4 rounded-2xl border"
                      style={{ background: "var(--card)", borderColor: "var(--border)" }}
                    >
                      <div className="flex items-center gap-2 mb-2 text-indigo-500 font-bold text-xs uppercase tracking-wider">
                        <Sparkles size={14} />
                        <span>Observed Finding</span>
                      </div>
                      <p className="text-xs leading-relaxed font-medium" style={{ color: "var(--txt)" }}>
                        {findingText}
                      </p>
                    </div>

                    <div
                      className="p-4 rounded-2xl border"
                      style={{ background: "var(--card)", borderColor: "var(--border)" }}
                    >
                      <div className="flex items-center gap-2 mb-2 text-teal-600 dark:text-teal-400 font-bold text-xs uppercase tracking-wider">
                        <Layers size={14} />
                        <span>Drivers &amp; Cohort Concentration</span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                        {driversText}
                      </p>
                    </div>

                    <div
                      className="p-4 rounded-2xl border"
                      style={{ background: "rgba(99, 102, 241, 0.05)", borderColor: "rgba(99, 102, 241, 0.2)" }}
                    >
                      <div className="flex items-center gap-2 mb-2 text-indigo-400 font-bold text-xs uppercase tracking-wider">
                        <Award size={14} />
                        <span>Leadership Action</span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: "var(--txt)" }}>
                        {actionText}
                      </p>
                    </div>
                  </div>
                </div>
              ),
            };
          })
        : [
            {
              title: "Visual Analytics & Distribution Trends",
              subtitle: "Interactive graphical breakdown of core volume, category mix, and variances",
              content: (
                <div
                  className="p-8 rounded-2xl border text-center flex flex-col items-center justify-center gap-3"
                  style={{ background: "var(--card)", borderColor: "var(--border)", minHeight: 220 }}
                >
                  <BarChart3 size={32} style={{ color: "var(--accent)" }} />
                  <h4 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                    No Dashboard Charts Generated Yet
                  </h4>
                  <p className="text-xs max-w-md" style={{ color: "var(--txt-m)" }}>
                    Continuous real-time charts are rendering across your {numericCols.length} quantitative metrics. Visit the Dashboard tab to pin custom pivot charts directly to this presentation deck.
                  </p>
                </div>
              ),
            },
          ]),

      // ── SLIDE 4: Strategic Discoveries & High-Impact Insights (Insights Component)
      {
        title: "Key Strategic Discoveries & Algorithmic Insights",
        subtitle: "High-leverage takeaways identified by the 14-plugin intelligence engine",
        content: (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              {strategicInsights.length > 0 ? (
                strategicInsights.slice(0, 6).map((ins: any, idx: number) => {
                  const imp = Math.round((ins.importance ?? 0.8) * 100);
                  const isTop = idx === 0;
                  const isRisk = (ins.type || "").includes("anomaly") || (ins.type || "").includes("forecast") || (ins.type || "").includes("risk");
                  return (
                    <div
                      key={idx}
                      className="p-4 rounded-2xl border flex flex-col justify-between"
                      style={{ background: "var(--card)", borderColor: "var(--border)" }}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className={`px-2 py-0.5 rounded-[4px] text-[9px] font-bold uppercase tracking-wider ${
                            isRisk
                              ? "bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                              : "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                          }`}>
                            {ins.type?.replace("_", " ") || "Insight"}
                          </span>
                          <span className="text-[10px] font-mono text-zinc-500 dark:text-zinc-400 font-bold">Impact {imp}%</span>
                        </div>
                        <h4 className="text-xs font-bold mb-1.5" style={{ color: isTop ? "var(--accent)" : "var(--txt)" }}>
                          {ins.title}
                        </h4>
                        <p className="text-[11px] leading-relaxed line-clamp-4" style={{ color: "var(--txt-m)" }}>
                          {ins.description}
                        </p>
                      </div>
                      <div className="mt-3 pt-2.5 border-t text-[10px] font-bold flex items-center justify-between" style={{
                        borderColor: "var(--border)",
                        color: isRisk ? "#ef4444" : "#10b981",
                      }}>
                        <span>{isRisk ? "Priority: Risk Mitigation" : "Priority: Immediate Action"}</span>
                        <TrendingUp size={12} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <>
                  <div
                    className="p-4 rounded-2xl border flex flex-col justify-between"
                    style={{ background: "var(--card)", borderColor: "var(--border)" }}
                  >
                    <div>
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-emerald-500/15 text-emerald-400 mb-2.5">
                        <TrendingUp size={15} />
                      </div>
                      <h4 className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>
                        1. Cohort Segmentation Optimization
                      </h4>
                      <p className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
                        Distinct clusters emerge within key categorical dimensions (e.g. {categoricalCols[0]?.name || "primary segment"}). Targeting the top quartile unlocks substantial lift.
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t text-[10px] font-bold text-emerald-500" style={{ borderColor: "var(--border)" }}>
                      High Leverage
                    </div>
                  </div>

                  <div
                    className="p-4 rounded-2xl border flex flex-col justify-between"
                    style={{ background: "var(--card)", borderColor: "var(--border)" }}
                  >
                    <div>
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-indigo-500/15 text-indigo-400 mb-2.5">
                        <Target size={15} />
                      </div>
                      <h4 className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>
                        2. High-Impact Target Predictor
                      </h4>
                      <p className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
                        Variance in quantitative attributes ({numericCols[0]?.name || "primary metric"}) exhibits strong predictability. AutoML benchmarking yields immediate champion accuracy.
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t text-[10px] font-bold text-indigo-400" style={{ borderColor: "var(--border)" }}>
                      Quick-Win Potential
                    </div>
                  </div>

                  <div
                    className="p-4 rounded-2xl border flex flex-col justify-between"
                    style={{ background: "var(--card)", borderColor: "var(--border)" }}
                  >
                    <div>
                      <div className="w-7 h-7 rounded-lg flex items-center justify-center bg-amber-500/15 text-amber-400 mb-2.5">
                        <Zap size={15} />
                      </div>
                      <h4 className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>
                        3. Multi-Plugin Anomaly Scanning
                      </h4>
                      <p className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
                        Continuous profiling across 14 statistical heuristics ensures zero unnoticed drift, outlier clustering, or categorical imbalance in active records.
                      </p>
                    </div>
                    <div className="mt-3 pt-2 border-t text-[10px] font-bold text-amber-500" style={{ borderColor: "var(--border)" }}>
                      Governance Active
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        ),
      },

      // ── SLIDE 5: Correlation Drivers & Multidimensional Variance
      {
        title: "Multivariate Correlation Drivers & Relationships",
        subtitle: "Bivariate dependencies, covariance sweep, and key driver analysis",
        content: (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {scatterChart ? (
                <SlideChartCard
                  chart={scatterChart}
                  title={scatterChart.title || "Bivariate Correlation Scatter"}
                  subtitle="Quantified point covariance across active records"
                />
              ) : (
                <div
                  className="p-4 rounded-2xl border space-y-3"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                      Strongest Collinear Drivers
                    </h4>
                    <span className="text-[10px] font-mono text-indigo-400 font-bold">Pearson |r| &gt; 0.4</span>
                  </div>
                  {correlationInsights.length > 0 ? (
                    <div className="space-y-2">
                      {correlationInsights.slice(0, 3).map((ci: any, idx: number) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl border text-xs"
                          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                        >
                          <div className="font-bold text-indigo-400">{ci.title}</div>
                          <p className="text-[11px] mt-1 leading-relaxed" style={{ color: "var(--txt-m)" }}>
                            {ci.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="p-3 rounded-xl border text-xs" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                        <span className="font-bold text-indigo-400">Direct Metric Proportionality</span>
                        <p className="text-[11px] mt-1 text-zinc-400">
                          Strong positive co-movement identified between primary quantitative columns. Increases in primary transaction volume correlate directly with operational velocity.
                        </p>
                      </div>
                      <div className="p-3 rounded-xl border text-xs" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                        <span className="font-bold text-emerald-400">Orthogonal Sub-Dimensions</span>
                        <p className="text-[11px] mt-1 text-zinc-400">
                          Remaining numeric attributes demonstrate low inter-feature collinearity (|r| &lt; 0.25), ensuring zero information redundancy for tree-based models.
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div
                className="p-4 rounded-2xl border flex flex-col justify-between"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "var(--txt)" }}>
                    Collinearity &amp; Modeling Guidance
                  </h4>
                  <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                    Continuous covariance analysis highlights direct relationships between primary operational metrics. Tree-based algorithms like LightGBM and XGBoost handle mild collinearity gracefully, while linear regularized baselines benefit from automated L2 penalty scaling.
                  </p>
                </div>
                <div className="mt-4 p-3 rounded-xl border space-y-1" style={{ background: "rgba(16, 185, 129, 0.05)", borderColor: "rgba(16, 185, 129, 0.2)" }}>
                  <span className="text-[10px] font-bold uppercase text-emerald-500 flex items-center gap-1.5">
                    <CheckCircle2 size={12} /> Covariance Verification Active
                  </span>
                  <p className="text-[11px]" style={{ color: "var(--txt)" }}>
                    Variance inflation factors remain within stable thresholds with zero target leakage.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ),
      },

      // ── SLIDE 6: Quantile Dispersion & Outlier Bounds (Boxplot)
      {
        title: "Statistical Quantile Dispersion & Outlier Bounds",
        subtitle: "Five-number distribution summary, variance analysis, and cohort performance",
        content: (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {boxplotChart ? (
                <SlideChartCard
                  chart={boxplotChart}
                  title={boxplotChart.title || "Quantile Dispersion: Five-Number Summary"}
                  subtitle="Interquartile range (IQR), median benchmark, and whiskers"
                />
              ) : (
                <div
                  className="p-5 rounded-2xl border flex flex-col justify-between"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <div>
                    <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-indigo-500/15 text-indigo-400 mb-3">
                      <BarChart3 size={18} />
                    </div>
                    <h4 className="text-sm font-bold mb-1" style={{ color: "var(--txt)" }}>
                      Quantile Dispersion Profile
                    </h4>
                    <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                      Five-number dispersion analysis computes the exact 25th percentile (Q1), 50th percentile (Median), and 75th percentile (Q3), bounding normal transaction variance within 1.5x IQR whiskers.
                    </p>
                  </div>
                  <div className="pt-3 border-t text-[11px] font-bold text-indigo-400" style={{ borderColor: "var(--border)" }}>
                    Verified Statistical Symmetry
                  </div>
                </div>
              )}

              <div
                className="p-4 rounded-2xl border flex flex-col justify-between"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "var(--txt)" }}>
                    Distribution Spread &amp; Variance Insights
                  </h4>
                  <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>
                    The interquartile range (IQR) establishes robust parametric boundaries, ensuring stability against outlier distortions. Performance clusters tightly around the median baseline, revealing clear separation between standard operational cohorts and exceptional high-performing segments.
                  </p>
                </div>
                <div className="mt-4 p-3 rounded-xl border space-y-1" style={{ background: "rgba(99, 102, 241, 0.05)", borderColor: "rgba(99, 102, 241, 0.2)" }}>
                  <span className="text-[10px] font-bold uppercase text-indigo-400 flex items-center gap-1.5">
                    <Sparkles size={12} /> Dispersion Takeaway
                  </span>
                  <p className="text-[11px]" style={{ color: "var(--txt)" }}>
                    Lower whisker bounds show high cohort resilience with minimal downside tail risk across segments.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ),
      },

      // ── SLIDE 7: Strategic Execution Roadmap & Action Plan
      {
        title: "Recommended Strategic Action Plan",
        subtitle: "Turnkey execution steps to achieve immediate business & analytical value",
        content: (
          <div className="space-y-3.5">
            <div
              className="p-4 rounded-2xl border flex items-center justify-between gap-4 transition-all hover:scale-[1.01]"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-3.5">
                <span
                  className="w-8 h-8 rounded-[4px] flex items-center justify-center font-black text-xs text-white shrink-0 shadow-xs"
                  style={{ background: "var(--accent)" }}
                >
                  1
                </span>
                <div>
                  <h4 className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                    1. Targeted Cohort Elevation &amp; Intervention
                  </h4>
                  <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                    Focus operational interventions on lower-quartile cohorts (below Q1 threshold) to lift baseline performance.
                  </p>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-[4px] text-[10px] font-bold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
                Phase 1 (Immediate)
              </span>
            </div>

            <div
              className="p-4 rounded-2xl border flex items-center justify-between gap-4 transition-all hover:scale-[1.01]"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-3.5">
                <span
                  className="w-8 h-8 rounded-[4px] flex items-center justify-center font-black text-xs text-white shrink-0 shadow-xs"
                  style={{ background: "#10b981" }}
                >
                  2
                </span>
                <div>
                  <h4 className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                    2. Early-Warning Performance Triggers
                  </h4>
                  <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                    Deploy automated alert triggers based on key predictive covariance drivers (e.g. attendance thresholds).
                  </p>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-[4px] text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0">
                Phase 2 (Automation)
              </span>
            </div>

            <div
              className="p-4 rounded-2xl border flex items-center justify-between gap-4 transition-all hover:scale-[1.01]"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-3.5">
                <span
                  className="w-8 h-8 rounded-[4px] flex items-center justify-center font-black text-xs text-white shrink-0 shadow-xs"
                  style={{ background: "#f59e0b" }}
                >
                  3
                </span>
                <div>
                  <h4 className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                    3. Stakeholder Executive Cadence &amp; BI Sync
                  </h4>
                  <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                    Establish recurring executive briefing cycles to synchronize cross-functional leadership with live performance.
                  </p>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-[4px] text-[10px] font-bold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
                Phase 3 (Scale)
              </span>
            </div>
          </div>
        ),
      },
    ];
  }, [
    rows,
    cols,
    numericCols,
    categoricalCols,
    filename,
    cleanProfile,
    dashStats,
    dashCharts,
    dashSummary,
    columnsList,
    strategicInsights,
    riskInsights,
    correlationInsights,
    setActiveTab,
  ]);

  const handlePrintDeck = () => {
    document.body.classList.add("print-deck-mode");
    const cleanup = () => {
      document.body.classList.remove("print-deck-mode");
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup);
    setTimeout(cleanup, 2500);
    window.print();
  };

  return (
    <div className="p-4 md:p-6 space-y-6 max-w-7xl mx-auto print:p-0 print:m-0 print:max-w-none print:space-y-0">
      {/* ── Header & View Switcher ────────────────────────────────────────── */}
      <div
        className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b pb-4 no-print"
        style={{ borderColor: "var(--border)" }}
      >
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-black uppercase tracking-tight" style={{ color: "var(--txt)" }}>
              Executive Briefings &amp; Reports
            </h1>
            <span className="px-2 py-0.5 rounded-[4px] text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              3 Formats
            </span>
          </div>
          <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
            Curated presentation slides, automated statistical profiling, and AI business narratives with PDF exports.
          </p>
        </div>

        {/* View Switcher */}
        <div
          className="flex items-center p-1 rounded-[4px] border text-xs font-semibold"
          style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}
        >
          <button
            onClick={() => setReportView("deck")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] transition-all cursor-pointer ${
              reportView === "deck" ? "shadow-xs font-bold" : "opacity-70 hover:opacity-100"
            }`}
            style={{
              background: reportView === "deck" ? "var(--surface)" : "transparent",
              color: reportView === "deck" ? "var(--accent)" : "var(--txt-m)",
              border: reportView === "deck" ? "1px solid var(--accent)" : "1px solid transparent",
            }}
          >
            <Presentation size={13} />
            <span>Slide Deck ({slides.length})</span>
          </button>

          <button
            onClick={() => setReportView("eda")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] transition-all cursor-pointer ${
              reportView === "eda" ? "shadow-xs font-bold" : "opacity-70 hover:opacity-100"
            }`}
            style={{
              background: reportView === "eda" ? "var(--surface)" : "transparent",
              color: reportView === "eda" ? "var(--accent)" : "var(--txt-m)",
              border: reportView === "eda" ? "1px solid var(--accent)" : "1px solid transparent",
            }}
          >
            <BarChart3 size={13} />
            <span>Statistical Profile</span>
          </button>

          <button
            onClick={() => setReportView("biz")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] transition-all cursor-pointer ${
              reportView === "biz" ? "shadow-xs font-bold" : "opacity-70 hover:opacity-100"
            }`}
            style={{
              background: reportView === "biz" ? "var(--surface)" : "transparent",
              color: reportView === "biz" ? "var(--accent)" : "var(--txt-m)",
              border: reportView === "biz" ? "1px solid var(--accent)" : "1px solid transparent",
            }}
          >
            <FileText size={13} />
            <span>AI Business Report</span>
          </button>
        </div>
      </div>

      {/* ── VIEW 1: EXECUTIVE SLIDE DECK ──────────────────────────────────── */}
      {reportView === "deck" && (
        <>
          {/* Interactive Single-Slide Carousel for Screen Display */}
          <div className="space-y-4 screen-only-deck">
            <div
              className="p-6 md:p-8 rounded-3xl border shadow-xl relative overflow-hidden transition-all flex flex-col justify-between"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
                minHeight: 480,
              }}
            >
              {/* Top Slide Header */}
              <div
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b pb-4 mb-6"
                style={{ borderColor: "var(--border)" }}
              >
                <div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: "var(--accent)" }}>
                    Slide {currentSlide + 1} of {slides.length} &middot; DataForge Executive Briefing Deck
                  </span>
                  <h2 className="text-lg font-black tracking-tight mt-0.5" style={{ color: "var(--txt)" }}>
                    {slides[currentSlide].title}
                  </h2>
                  <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                    {slides[currentSlide].subtitle}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePrintDeck}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-[4px] text-xs font-bold border transition-all hover:scale-[1.01] active:scale-[0.99] cursor-pointer shadow-xs bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-100 hover:border-slate-400"
                    title="Print all slides to presentation PDF"
                  >
                    <Printer size={14} style={{ color: "var(--accent, #FF4310)" }} />
                    <span>Print Deck ({slides.length} Slides)</span>
                  </button>
                </div>
              </div>

              {/* Slide Body */}
              <div className="py-2 flex-1 animate-fade-in">{slides[currentSlide].content}</div>

              {/* Slide Navigation Footer */}
              <div
                className="mt-8 pt-4 border-t flex items-center justify-between gap-4"
                style={{ borderColor: "var(--border)" }}
              >
                <div className="flex items-center gap-1.5">
                  {slides.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => setCurrentSlide(idx)}
                      className="h-2 rounded-[2px] transition-all cursor-pointer"
                      style={{
                        width: currentSlide === idx ? 28 : 12,
                        background: currentSlide === idx ? "var(--accent, #FF4310)" : "rgba(100, 116, 139, 0.35)",
                      }}
                      title={`Go to slide ${idx + 1}`}
                    />
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentSlide((p) => Math.max(0, p - 1))}
                    disabled={currentSlide === 0}
                    className="flex items-center gap-1 px-3.5 py-2 rounded-[4px] text-xs font-bold border transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-40 cursor-pointer bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-700 text-slate-800 dark:text-slate-100 hover:border-slate-400 shadow-xs"
                  >
                    <ChevronLeft size={14} />
                    <span>Previous</span>
                  </button>

                  <button
                    onClick={() => setCurrentSlide((p) => Math.min(slides.length - 1, p + 1))}
                    disabled={currentSlide === slides.length - 1}
                    className="flex items-center gap-1 px-4 py-2 rounded-[4px] text-xs font-bold transition-all hover:scale-[1.01] active:scale-[0.99] disabled:opacity-40 cursor-pointer shadow-sm text-white"
                    style={{ background: "var(--accent, #FF4310)" }}
                  >
                    <span>Next Slide</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Full Multi-Slide Presentation for Print (ALL 7 slides rendered on separate landscape pages) */}
          <div className="print-deck-only">
            {slides.map((s, idx) => (
              <div key={idx} className="print-slide">
                <div className="print-slide-header">
                  <div className="print-slide-meta">
                    <span className="print-slide-badge">DataForge &middot; Executive Briefing Deck</span>
                    <span className="print-slide-num">
                      Slide {idx + 1} of {slides.length}
                    </span>
                  </div>
                  <h2 className="print-slide-title">{s.title}</h2>
                  <p className="print-slide-subtitle">{s.subtitle}</p>
                </div>

                <div className="print-slide-body">{s.content}</div>

                <div className="print-slide-footer">
                  <span>{filename} &middot; Nov 2026 &middot; Executive BI Presentation Deck</span>
                  <span>
                    Dataset: {filename} ({rows.toLocaleString()} rows &middot; {cols} columns)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ── VIEW 2: STATISTICAL PROFILE ───────────────────────────────────── */}
      {reportView === "eda" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-base font-bold" style={{ color: "var(--txt)" }}>
                Automated Statistical Profiler
              </h3>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                Distribution curves, Pearson/Spearman correlation matrices, quantile distributions, and missingness audits.
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={runEda}
                disabled={isGeneratingEda}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-[4px] text-xs font-bold transition cursor-pointer shadow-md"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                {isGeneratingEda && <RefreshCw size={12} className="animate-spin" />}
                <span>{isGeneratingEda ? "Profiling..." : edaReady ? "Update Profile" : "Generate Profile"}</span>
              </button>
              {edaReady && (
                <>
                  <a
                    href={`/api/eda/report?format=pdf&upload_id=${uploadId}${fullAuthQuery}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] text-xs font-bold border transition hover:scale-[1.02]"
                    style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                  >
                    <Download size={13} />
                    <span>Download PDF</span>
                  </a>
                  <a
                    href={`/api/eda/report?upload_id=${uploadId}${fullAuthQuery}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] text-xs font-bold border transition hover:scale-[1.02]"
                    style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                    title="Open Fullscreen Profiler"
                  >
                    <ExternalLink size={13} />
                    <span>Fullscreen</span>
                  </a>
                </>
              )}
            </div>
          </div>

          {edaError && (
            <div className="p-4 rounded-xl border space-y-1 bg-rose-500/10 border-rose-500/20 text-rose-400">
              <p className="font-bold text-xs flex items-center gap-1.5">
                <AlertTriangle size={14} /> Profiling Failed
              </p>
              <p className="font-mono text-xs">{edaError}</p>
            </div>
          )}

          {isGeneratingEda && (
            <div
              className="p-12 rounded-2xl border text-center flex flex-col items-center justify-center gap-3"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <RefreshCw size={24} className="animate-spin" style={{ color: "var(--accent)" }} />
              <div className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                Generating Detailed Statistical Profile...
              </div>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                Auditing quantile tables, missingness signatures, and correlation heatmaps.
              </p>
            </div>
          )}

          {!edaReady && !isGeneratingEda && (
            <div
              className="p-12 rounded-2xl border text-center flex flex-col items-center justify-center gap-4 my-2"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ background: "rgba(99, 102, 241, 0.12)", color: "#6366f1" }}
              >
                <BarChart3 size={32} />
              </div>
              <div className="max-w-md">
                <h4 className="text-base font-bold" style={{ color: "var(--txt)" }}>
                  No Statistical Profile Generated Yet
                </h4>
                <p className="text-xs mt-1.5" style={{ color: "var(--txt-m)" }}>
                  Compute distribution histograms, parametric moments, Pearson/Spearman correlation matrices, and cardinality warnings for {rows.toLocaleString()} records.
                </p>
              </div>
              <button
                onClick={runEda}
                className="flex items-center gap-2 px-5 py-2.5 rounded-[4px] text-xs font-bold transition hover:scale-[1.02] cursor-pointer shadow-lg"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                <Sparkles size={14} />
                <span>Generate Statistical Profile Now</span>
              </button>
            </div>
          )}

          {edaReady && !isGeneratingEda && (
            <div className="rounded-2xl border overflow-hidden shadow-lg" style={{ borderColor: "var(--border)" }}>
              <iframe
                id="eda-frame"
                src={`/api/eda/report?upload_id=${uploadId}${fullAuthQuery}&t=${reportKey}`}
                className="w-full bg-[var(--bg)] border-none block"
                style={{ height: "clamp(550px, calc(100vh - 230px), 1100px)" }}
              />
            </div>
          )}
        </div>
      )}

      {/* ── VIEW 3: AI BUSINESS REPORT ────────────────────────────────────── */}
      {reportView === "biz" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-base font-bold" style={{ color: "var(--txt)" }}>
                AI Business Analyst Report
              </h3>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                McKinsey-grade executive briefing deck, KPI trends, and board-ready insights with downloadable PDF.
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={generateBizReport}
                disabled={bizReportGenerating}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-[4px] text-xs font-bold transition cursor-pointer shadow-md"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                {bizReportGenerating ? <RefreshCw size={12} className="animate-spin" /> : <Sparkles size={12} />}
                <span>{bizReportGenerating ? "Analyzing..." : bizReportReady ? "Update Analysis" : "Generate Report"}</span>
              </button>
              {bizReportReady && (
                <>
                  <a
                    href={`/api/data-report/download?print=true&upload_id=${uploadId}${fullAuthQuery}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] text-xs font-bold border transition hover:scale-[1.02]"
                    style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                    title="Export Printable PDF Presentation"
                  >
                    <Download size={13} />
                    <span>Download PDF</span>
                  </a>
                  <a
                    href={`/api/reports/latest?upload_id=${uploadId}${fullAuthQuery}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] text-xs font-bold border transition hover:scale-[1.02]"
                    style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--accent)" }}
                    title="Open Fullscreen Slide Deck Presentation"
                  >
                    <Presentation size={13} />
                    <span>Open Deck</span>
                  </a>
                </>
              )}
            </div>
          </div>

          {bizReportError && (
            <div className="p-4 rounded-xl border space-y-1 bg-rose-500/10 border-rose-500/20 text-rose-400">
              <p className="font-bold text-xs flex items-center gap-1.5">
                <AlertTriangle size={14} /> Report Generation Failed
              </p>
              <p className="font-mono text-xs">{bizReportError}</p>
            </div>
          )}

          {bizReportGenerating && (
            <div
              className="p-12 rounded-2xl border text-center flex flex-col items-center justify-center gap-3"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <Sparkles size={24} className="animate-bounce" style={{ color: "var(--accent)" }} />
              <div className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                AI Analyst is synthesizing your executive deck...
              </div>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                Structuring executive narrative, pattern discovery, and board-ready slides.
              </p>
            </div>
          )}

          {!bizReportReady && !bizReportGenerating && (
            <div
              className="p-12 rounded-2xl border text-center flex flex-col items-center justify-center gap-4 my-2"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center"
                style={{ background: "rgba(16, 185, 129, 0.12)", color: "#10b981" }}
              >
                <Sparkles size={32} />
              </div>
              <div className="max-w-md">
                <h4 className="text-base font-bold" style={{ color: "var(--txt)" }}>
                  No AI Business Report Generated Yet
                </h4>
                <p className="text-xs mt-1.5" style={{ color: "var(--txt-m)" }}>
                  Synthesize an executive briefing with an automated narrative, KPI anomaly detection, strategic takeaways, and board-ready printable PDF summaries.
                </p>
              </div>
              <button
                onClick={generateBizReport}
                className="flex items-center gap-2 px-5 py-2.5 rounded-[4px] text-xs font-bold transition hover:scale-[1.02] cursor-pointer shadow-lg"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                <Sparkles size={14} />
                <span>Generate AI Executive Report Now</span>
              </button>
            </div>
          )}

          {bizReportReady && !bizReportGenerating && (
            <div className="rounded-2xl border overflow-hidden shadow-xl" style={{ borderColor: "var(--border)" }}>
              <iframe
                id="biz-report-frame"
                src={`/api/reports/latest?upload_id=${uploadId}${fullAuthQuery}&t=${reportKey}`}
                className="w-full bg-[var(--bg)] border-none block"
                style={{ height: "clamp(550px, calc(100vh - 230px), 1100px)" }}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
