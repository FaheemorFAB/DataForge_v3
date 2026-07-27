"use client";

import React, { useState, useEffect } from "react";
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
  Filler
} from 'chart.js';
import { RefreshCw, X, BarChart4 } from 'lucide-react';
import { Scatter, Line, Bar, Pie } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const BoxPlotVisualizer = ({ data, formatted }: { data: any, formatted: any }) => {
    if (!data || typeof data.min !== 'number') return <p className="text-gray-500 text-xs text-center py-10">Invalid Data</p>;
    const range = data.max - data.min;
    const pad = range === 0 ? 1 : range * 0.1;
    const minX = data.min - pad;
    const maxX = data.max + pad;
    const total = maxX - minX;

    const toPct = (val: number) => `${Math.max(0, Math.min(100, ((val - minX) / total) * 100))}%`;

    return (
        <div className="w-full h-full flex flex-col justify-center px-4 text-gray-300 relative">
            <div className="relative w-full h-16 flex items-center mb-6 mt-4">
                {/* Horizontal line for whiskers */}
                <div className="absolute h-[2px] bg-gray-600 rounded" style={{ left: toPct(data.min), right: `${100 - parseFloat(toPct(data.max))}%` }} />
                
                {/* Min whisker */}
                <div className="absolute w-[3px] h-6 bg-gray-400 rounded" style={{ left: toPct(data.min), top: '50%', transform: 'translate(-50%, -50%)' }} />
                
                {/* Max whisker */}
                <div className="absolute w-[3px] h-6 bg-gray-400 rounded" style={{ left: toPct(data.max), top: '50%', transform: 'translate(-50%, -50%)' }} />
                
                {/* IQR Box */}
                <div className="absolute h-10 rounded-sm" style={{ left: toPct(data.q1), width: `${((data.q3 - data.q1) / total) * 100}%`, background: 'rgba(46,91,255,0.25)', border: '2px solid #2e5bff', top: '50%', transform: 'translateY(-50%)', boxShadow: '0 0 10px rgba(46,91,255,0.1)' }} />
                
                {/* Median Line */}
                <div className="absolute w-[3px] h-10 rounded" style={{ left: toPct(data.median), top: '50%', transform: 'translate(-50%, -50%)', background: '#f59e0b', zIndex: 10 }} />
                
                {/* Tooltips or Labels */}
                <div className="absolute text-[10px] font-mono text-gray-400 -bottom-6" style={{ left: toPct(data.min), transform: 'translateX(-50%)' }}>{formatted?.min}</div>
                <div className="absolute text-[10px] font-mono text-gray-400 -bottom-6" style={{ left: toPct(data.max), transform: 'translateX(-50%)' }}>{formatted?.max}</div>
                <div className="absolute text-[11px] font-mono font-bold text-[#f59e0b] -top-7" style={{ left: toPct(data.median), transform: 'translateX(-50%)' }}>{formatted?.median}</div>
            </div>
            
            <div className="flex justify-between items-center w-full mt-auto pt-4 border-t border-gray-800">
                <div className="text-center w-1/3">
                    <p className="text-[9px] text-gray-500 uppercase tracking-wider">Q1</p>
                    <p className="font-mono text-xs text-gray-300">{formatted?.q1}</p>
                </div>
                <div className="text-center w-1/3 border-l border-r border-gray-800">
                    <p className="text-[9px] text-gray-500 uppercase tracking-wider">Median</p>
                    <p className="font-mono text-sm font-bold text-[#f59e0b]">{formatted?.median}</p>
                </div>
                <div className="text-center w-1/3">
                    <p className="text-[9px] text-gray-500 uppercase tracking-wider">Q3</p>
                    <p className="font-mono text-xs text-gray-300">{formatted?.q3}</p>
                </div>
            </div>
        </div>
    );
};

export function DashboardTab() {
  const { uploadId, profile } = useWorkspace();
  const [isDashLoading, setIsDashLoading] = useState(false);
  const [dashStats, setDashStats] = useState<any[]>([]);
  const [dashCharts, setDashCharts] = useState<any[]>([]);
  const [dashSummary, setDashSummary] = useState("");
  const [dashIdStats, setDashIdStats] = useState<any>(null);
  const [dashRecent, setDashRecent] = useState<any[]>([]);
  const [dashDim, setDashDim] = useState("Category");
  const [dashMetric, setDashMetric] = useState("Metric");
  const [dashNumericCols, setDashNumericCols] = useState<string[]>([]);
  const [profileCols, setProfileCols] = useState<string[]>([]);

  const [customChart, setCustomChart] = useState({ id: null as any, chart_type: 'bar', x_col: '', y_col: '', agg_type: 'mean', title: '', is_area: false, top_n: 10 });
  const [isGeneratingChart, setIsGeneratingChart] = useState(false);
  const [customChartError, setCustomChartError] = useState("");

  useEffect(() => {
    if (uploadId) {
      loadDashboard();
    }
  }, [uploadId]);

  const loadDashboard = async () => {
    setIsDashLoading(true);
    try {
      const res = await apiFetch("/dashboard/stats", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chart_dim: "", chart_metric: "", upload_id: uploadId })
      });
      if (res.ok) {
        const d = await res.json();
        setDashStats(d.stats || []);
        setDashCharts(d.charts || []);
        setDashSummary(d.summary || "");
        setDashIdStats(d.id_stats || null);
        setDashRecent(d.recent_data || []);
        setDashDim(d.dim || "Category");
        setDashMetric(d.metric || "Metric");
        setDashNumericCols(d.numeric_cols || []);
        if (d.cat_cols) {
          setProfileCols([...(d.cat_cols || []), ...(d.numeric_cols || [])]);
        } else {
            setProfileCols(profile?.columns?.map((c: any) => c.name) || []);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsDashLoading(false);
    }
  };

  const saveCustomChart = async () => {
    setCustomChartError('');
    setIsGeneratingChart(true);
    try {
      const payload = { ...customChart, upload_id: uploadId };
      const res = await apiFetch("/dashboard/custom-chart", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const d = await res.json();
        setCustomChartError(d.error || 'Failed to generate chart');
        setIsGeneratingChart(false);
        return;
      }
      const d = await res.json();
      if (d.error) {
        setCustomChartError(d.error);
      } else {
        setCustomChart({ id: null, chart_type: 'bar', x_col: '', y_col: '', agg_type: 'mean', title: '', is_area: false, top_n: 10 });
        await loadDashboard();
      }
    } catch (e: any) {
      setCustomChartError('Network error: ' + (e.message || String(e)));
    } finally {
      setIsGeneratingChart(false);
    }
  };

  const removeChart = async (ch: any) => {
    if (!ch.is_custom) return; // Currently only supporting deleting custom charts
    try {
      const res = await apiFetch("/dashboard/custom-chart/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, chart_id: ch.id })
      });
      if (res.ok) {
        setDashCharts(prev => prev.filter(c => c.id !== ch.id));
      } else {
        console.error("Failed to delete chart on backend");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const renderChartData = (ch: any) => {
    const commonOptions: any = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { 
        legend: { display: ch.type === 'pie', labels: { color: 'rgba(255,255,255,0.7)' } } 
      },
      scales: ch.type === 'pie' ? undefined : {
        x: { 
          title: { display: true, text: ch.x_label || ch.x_col || 'X-Axis', color: 'rgba(255,255,255,0.5)', font: { size: 9, weight: 'bold' } },
          ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } }, 
          grid: { color: 'rgba(255,255,255,0.06)' } 
        },
        y: { 
          title: { display: true, text: ch.y_label || ch.y_col || 'Y-Axis', color: 'rgba(255,255,255,0.5)', font: { size: 9, weight: 'bold' } },
          ticks: { color: 'rgba(255,255,255,0.4)', font: { size: 9 } }, 
          grid: { color: 'rgba(255,255,255,0.06)' } 
        }
      }
    };

    if (ch.type === 'scatter') {
      const pts = (ch.values && ch.values.length > 0 && typeof ch.values[0] === 'object' && ch.values[0].x !== undefined)
        ? ch.values // Backend already returned [{x, y}, ...]
        : ch.values.map((v: any, i: number) => ({ x: ch.labels[i], y: v }));
      
      return <Scatter data={{ datasets: [{ data: pts, backgroundColor: 'rgba(46,91,255,0.5)', pointRadius: 3 }] }} options={commonOptions} />;
    } else if (ch.type === 'line') {
      return <Line data={{ labels: ch.labels, datasets: [{ data: ch.values, borderColor: '#2e5bff', backgroundColor: 'rgba(46,91,255,0.1)', borderWidth: 2, fill: true, tension: 0.2, pointRadius: 2 }] }} options={commonOptions} />;
    } else if (ch.type === 'pie') {
      return <Pie data={{ labels: ch.labels, datasets: [{ data: ch.values, backgroundColor: ['#2e5bff','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#f97316','#84cc16','#14b8a6'] }] }} options={commonOptions} />;
    } else {
      return <Bar data={{ labels: ch.labels, datasets: [{ data: ch.values, backgroundColor: 'rgba(46,91,255,0.8)' }] }} options={commonOptions} />;
    }
  };

  return (
    <div className="tab-panel space-y-5 px-4 py-4 md:px-6 md:py-6">
      <div className="sec-hd flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
            ANALYTICS DASHBOARD
          </h2>
          <p className="sec-sub text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>
            KPIs · Trend Charts · Category Analysis · Distribution
          </p>
        </div>
        <div>
          <button onClick={loadDashboard} disabled={isDashLoading} className="bp">
            {isDashLoading && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>}
            <span className="flex items-center gap-1.5">{isDashLoading ? 'GENERATING...' : <><RefreshCw size={14} /> {dashStats.length ? 'UPDATE DASHBOARD' : 'GENERATE DASHBOARD'}</>}</span>
          </button>
        </div>
      </div>

      {isDashLoading && dashStats.length === 0 && (
        <div className="space-y-6 animate-pulse mt-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                    <div key={`skel-stat-${i}`} className="gc p-4 rounded-xl flex flex-col justify-center h-[100px]">
                      <div className="h-2.5 w-16 rounded mb-3" style={{ background: "var(--border)", opacity: 0.5 }}></div>
                      <div className="h-7 w-20 rounded" style={{ background: "var(--border)", opacity: 0.6 }}></div>
                    </div>
                ))}
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-5">
                    {Array.from({ length: 4 }).map((_, i) => (
                        <div key={`skel-chart-${i}`} className="rounded-2xl p-5 h-[280px]" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.05)" }}>
                            <div className="h-3 w-32 rounded mb-8" style={{ background: "var(--border)", opacity: 0.5 }}></div>
                            <div className="h-[180px] w-full rounded" style={{ background: "var(--border)", opacity: 0.3 }}></div>
                        </div>
                    ))}
                </div>
                <div className="space-y-5">
                    <div className="gc rounded-2xl p-5 h-[200px]">
                        <div className="h-3 w-24 rounded mb-5" style={{ background: "var(--border)", opacity: 0.5 }}></div>
                        <div className="space-y-3">
                            <div className="h-2 w-full rounded" style={{ background: "var(--border)", opacity: 0.3 }}></div>
                            <div className="h-2 w-full rounded" style={{ background: "var(--border)", opacity: 0.3 }}></div>
                            <div className="h-2 w-3/4 rounded" style={{ background: "var(--border)", opacity: 0.3 }}></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      )}

      {dashStats.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {dashStats.map(stat => (
            <div key={stat.label} className="gc p-4 rounded-xl">
              <p className="sl mb-1 truncate">{stat.label}</p>
              <p className="text-3xl font-black tracking-tighter" style={{ color: stat.color || "var(--accent)" }}>{stat.value.toLocaleString()}</p>
              <p className="text-[10px] mt-1 truncate font-semibold" style={{ color: stat.color || "var(--txt-m)" }}>{stat.sub}</p>
            </div>
          ))}
        </div>
      )}

      {/* Chart Builder */}
      {dashStats.length > 0 && (
        <div className="rounded-2xl overflow-hidden" style={{ background: "linear-gradient(135deg,rgba(46,91,255,.06) 0%,rgba(99,102,241,.04) 100%)", border: "1px solid rgba(46,91,255,.2)" }}>
          <div className="flex items-center justify-between px-5 py-4" style={{ background: "linear-gradient(135deg,rgba(46,91,255,.12),rgba(99,102,241,.08))", borderBottom: "1px solid rgba(46,91,255,.15)" }}>
              <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: "linear-gradient(135deg,var(--accent),rgba(99,102,241,.9))" }}>
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/></svg>
                  </div>
                  <div>
                      <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>Custom Chart Builder</h3>
                      <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>Create on-demand visualizations for specific columns</p>
                  </div>
              </div>
          </div>
          <div className="p-5 space-y-5">
              <div className="flex flex-wrap gap-2">
                  <button onClick={() => setCustomChart({...customChart, chart_type: 'bar'})} className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider ${customChart.chart_type === 'bar' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'}`}>Bar</button>
                  <button onClick={() => setCustomChart({...customChart, chart_type: 'line'})} className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider ${customChart.chart_type === 'line' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'}`}>Line</button>
                  <button onClick={() => setCustomChart({...customChart, chart_type: 'scatter'})} className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider ${customChart.chart_type === 'scatter' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'}`}>Scatter</button>
                  <button onClick={() => setCustomChart({...customChart, chart_type: 'pie'})} className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider ${customChart.chart_type === 'pie' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'}`}>Pie</button>
                  <button onClick={() => setCustomChart({...customChart, chart_type: 'boxplot'})} className={`px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wider ${customChart.chart_type === 'boxplot' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'}`}>Box Plot</button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="space-y-1.5">
                      <label className="sl">{customChart.chart_type === 'pie' ? 'Category' : 'X Axis / Category'}</label>
                      <select value={customChart.x_col} onChange={e => setCustomChart({...customChart, x_col: e.target.value})} className="inp w-full" style={{ padding: ".5rem", borderRadius: ".5rem", background: "var(--surface)", border: "1px solid rgba(46,91,255,.2)" }}>
                          <option value="">- Select -</option>
                          {profileCols.map(c => <option key={c} value={c}>{c}</option>)}
                      </select>
                  </div>
                  {!['histogram','boxplot'].includes(customChart.chart_type) && (
                      <div className="space-y-1.5">
                          <label className="sl">{customChart.chart_type === 'pie' ? 'Value (Numeric)' : 'Y Axis (Numeric)'}</label>
                          <select value={customChart.y_col} onChange={e => setCustomChart({...customChart, y_col: e.target.value})} className="inp w-full" style={{ padding: ".5rem", borderRadius: ".5rem", background: "var(--surface)", border: "1px solid rgba(46,91,255,.2)" }}>
                              <option value="">- Count Rows -</option>
                              {dashNumericCols.map(c => <option key={c} value={c}>{c}</option>)}
                          </select>
                      </div>
                  )}
                  {!['histogram','boxplot','scatter'].includes(customChart.chart_type) && (
                      <div className="space-y-1.5">
                          <label className="sl">Aggregation</label>
                          <select value={customChart.agg_type} onChange={e => setCustomChart({...customChart, agg_type: e.target.value})} className="inp w-full" style={{ padding: ".5rem", borderRadius: ".5rem", background: "var(--surface)", border: "1px solid rgba(46,91,255,.2)" }}>
                              <option value="mean">Average (Mean)</option>
                              <option value="sum">Sum</option>
                              <option value="count">Count of Values</option>
                              <option value="none">None - Raw Rows</option>
                          </select>
                      </div>
                  )}
                  {customChart.chart_type === 'pie' && (
                      <div className="space-y-1.5">
                          <label className="sl">Top N Slices</label>
                          <select value={customChart.top_n} onChange={e => setCustomChart({...customChart, top_n: parseInt(e.target.value)})} className="inp w-full" style={{ padding: ".5rem", borderRadius: ".5rem", background: "var(--surface)", border: "1px solid rgba(46,91,255,.2)" }}>
                              <option value={5}>Top 5</option>
                              <option value={10}>Top 10</option>
                              <option value={20}>Top 20</option>
                              <option value={500}>All (Limit 500)</option>
                          </select>
                      </div>
                  )}
              </div>
              <div className="flex gap-3 items-end">
                  <div className="flex-1 space-y-1.5">
                      <label className="sl">Custom Title</label>
                      <input type="text" value={customChart.title} onChange={e => setCustomChart({...customChart, title: e.target.value})} placeholder="Auto-generated if blank" className="inp w-full" style={{ padding: ".5rem", borderRadius: ".5rem", background: "var(--surface)", border: "1px solid rgba(46,91,255,.2)" }} />
                  </div>
                  <button onClick={saveCustomChart} disabled={isGeneratingChart || !customChart.x_col} className={`bp ${!customChart.x_col || isGeneratingChart ? 'opacity-50 cursor-not-allowed' : ''}`}>
                      {isGeneratingChart ? 'Saving...' : 'Add to Dashboard'}
                  </button>
              </div>
              {customChartError && <p className="text-red-400 text-xs">{customChartError}</p>}
          </div>
        </div>
      )}

      {/* Grid */}
      {(dashCharts.length > 0 || dashIdStats) && (
        <div className="space-y-6">
          {dashIdStats && (
              <div className="gc rounded-2xl p-5">
                  <p className="font-bold text-xs uppercase tracking-widest mb-4" style={{ color: "var(--txt-m)" }}>ID STATISTICS</p>
                  <div className="flex items-center justify-start gap-12">
                      <div><p className="sl mb-1">Total</p><p className="text-2xl font-black text-indigo-400">{dashIdStats.total}</p></div>
                      <div><p className="sl mb-1">Min</p><p className="text-lg font-black">{dashIdStats.min}</p></div>
                      <div><p className="sl mb-1">Max</p><p className="text-lg font-black">{dashIdStats.max}</p></div>
                  </div>
              </div>
          )}

          {dashCharts.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {dashCharts.map(ch => (
                    <div key={ch.id} className="rounded-2xl p-5 border-l-4 flex flex-col justify-between shadow-lg" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.08)", borderLeftColor: ch.is_custom ? 'var(--accent)' : '#2e5bff' }}>
                        <div className="flex items-center justify-between mb-4">
                            <p className="font-extrabold text-xs uppercase tracking-wider truncate">{ch.title}</p>
                            <button onClick={() => removeChart(ch)} className="text-gray-400 hover:text-red-500"><X size={14} /></button>
                        </div>
                        {ch.type === 'boxplot' ? (
                            <div style={{ height: "220px", position: "relative" }}>
                                <BoxPlotVisualizer data={ch.values} formatted={ch.formatted_values} />
                            </div>
                        ) : (
                            <div style={{ height: "220px", position: "relative" }}>
                                {renderChartData(ch)}
                            </div>
                        )}
                    </div>
                ))}
            </div>
          )}
        </div>
      )}

      {!dashStats.length && !isDashLoading && (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
            <div className="w-20 h-20 rounded-full flex items-center justify-center" style={{ background: "rgba(46,91,255,.08)" }}>
                <BarChart4 size={36} className="text-indigo-500" />
            </div>
            <p className="text-sm max-w-xs" style={{ color: "var(--txt-m)" }}>Click 'Generate Dashboard' to automatically build your KPI metrics, trend charts, and distribution analysis.</p>
        </div>
      )}
    </div>
  );
}
