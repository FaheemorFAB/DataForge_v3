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
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Scatter, Line, Bar } from 'react-chartjs-2';
import { Sparkles, Brain, AlertTriangle } from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

export function InsightsTab() {
  const { profile, uploadId } = useWorkspace();
  const [insightTopN, setInsightTopN] = useState("6");
  const [isRunningInsights, setIsRunningInsights] = useState(false);
  const [insightError, setInsightError] = useState("");
  const [insightCards, setInsightCards] = useState<any[]>([]);
  const [insightSummary, setInsightSummary] = useState("");
  const [insightSchema, setInsightSchema] = useState<any>(null);

  const runInsights = async () => {
    setIsRunningInsights(true);
    setInsightError("");
    setInsightCards([]);
    try {
      const res = await apiFetch("/insights/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          top_n: parseInt(insightTopN),
          use_gemini: false,
          upload_id: uploadId
        }),
      });

      if (!res.ok) {
        let errStr = "Failed to run insights.";
        try {
          const text = await res.text();
          let data;
          try { data = JSON.parse(text); } catch (e) { errStr = `HTTP ${res.status}: ${text.substring(0, 100)}`; }
          if (data && data.error) errStr = data.error;
        } catch (e) {}
        setInsightError(errStr);
        setIsRunningInsights(false);
        return;
      }

      const data = await res.json();
      if (data.error) {
        setInsightError(data.error);
        setIsRunningInsights(false);
        return;
      }

      if (data.sync || !data.task_id) {
        setInsightCards(data.insights || []);
        setInsightSummary(data.summary || "");
        setInsightSchema(data.schema || null);
        setIsRunningInsights(false);
        return;
      }

      // Polling fallback
      const pollTask = async (taskId: string) => {
        while (true) {
          await new Promise(r => setTimeout(r, 2000));
          const pRes = await apiFetch(`/tasks/status/${taskId}`);
          if (!pRes.ok) throw new Error("Task check failed");
          const pData = await pRes.json();
          if (pData.status === "completed") {
            return true;
          }
          if (pData.status === "failed") {
            throw new Error(pData.error || "Insight generation failed");
          }
        }
      };

      await pollTask(data.task_id);
      
      const cRes = await apiFetch("/insights/current");
      if (cRes.ok) {
        const cData = await cRes.json();
        setInsightCards(cData.insights || []);
        setInsightSummary(cData.summary || "");
        setInsightSchema(cData.schema || null);
      }

    } catch (e: any) {
      setInsightError(String(e.message || e));
    } finally {
      setIsRunningInsights(false);
    }
  };

  const parseInsightStats = (ins: any) => {
    const d = ins.description || '';
    let count = null, value = null, sigma = null, pct = null, prev = null, curr = null, date = null;

    const countM = d.match(/(\d[\d,]*)\s+anomalies?\s+found|anomalies?\s+found[:\s]+(\d[\d,]*)/i);
    if (countM) count = parseInt((countM[1] || countM[2]).replace(/,/g, ''));

    const valM = d.match(/[Vv]alue was ([\d,\.]+)/);
    if (valM) value = parseFloat(valM[1].replace(/,/g, '')).toLocaleString(undefined, { maximumFractionDigits: 0 });

    const sigM = d.match(/([\d\.]+)\s*[σx]|from mean[:\s]+([\d\.]+)/);
    if (sigM) sigma = parseFloat(sigM[1] || sigM[2]).toFixed(1);

    const pctM = d.match(/([\d\.]+)%/);
    if (pctM) {
      pct = parseFloat(pctM[1]).toFixed(1);
      if (/\b(down|declin|decreas|fell|drop)\b/i.test(d)) pct = '-' + pct;
    }

    const vsM = d.match(/\(([\d,\.]+)\s+vs\s+([\d,\.]+)\)/i);
    if (vsM) { curr = vsM[1]; prev = vsM[2]; }

    const dateM = d.match(/\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s\-]\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2}/i);
    if (dateM) date = dateM[0];

    return { count, value, sigma, pct, prev, curr, date };
  };

  const insightBadgeStyle = (type: string) => {
    const map: Record<string, any> = {
      trend: { background: 'rgba(99,102,241,.15)', color: '#6366F1' },
      ranking: { background: 'rgba(16,185,129,.15)', color: '#10B981' },
      correlation: { background: 'rgba(245,158,11,.15)', color: '#F59E0B' },
      anomaly: { background: 'rgba(239,68,68,.15)', color: '#EF4444' },
      distribution: { background: 'rgba(59,130,246,.15)', color: '#3B82F6' },
      contribution: { background: 'rgba(20,184,166,.15)', color: '#14B8A6' },
      segment: { background: 'rgba(139,92,246,.15)', color: '#8B5CF6' },
      change: { background: 'rgba(236,72,153,.15)', color: '#EC4899' },
    };
    return map[type] || { background: 'rgba(46,91,255,.1)', color: 'var(--accent)' };
  };

  const renderChart = (ins: any) => {
    if (!ins.chart_data) return null;
    const cd = ins.chart_data;
    const commonOptions: any = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: 'var(--txt-m)', font: { size: 9 } }, grid: { color: 'var(--border)' } },
        y: { ticks: { color: 'var(--txt-m)', font: { size: 9 } }, grid: { color: 'var(--border)' } }
      }
    };

    if (ins.chart === 'scatter') {
      const pts = (cd.x || []).map((x: any, j: number) => ({ x, y: (cd.y || [])[j] }));
      return (
        <Scatter 
          data={{
            datasets: [{ data: pts, backgroundColor: 'rgba(46,91,255,0.5)', pointRadius: 3 }]
          }}
          options={commonOptions}
        />
      );
    } else if (ins.chart === 'line') {
      return (
        <Line 
          data={{
            labels: cd.x || [],
            datasets: [{ data: cd.y || [], borderColor: '#2e5bff', backgroundColor: 'rgba(46,91,255,0.1)', borderWidth: 2, fill: true, tension: 0.2, pointRadius: 2 }]
          }}
          options={commonOptions}
        />
      );
    } else {
      return (
        <Bar 
          data={{
            labels: cd.x || [],
            datasets: [{ data: cd.y || [], backgroundColor: 'rgba(46,91,255,0.8)' }]
          }}
          options={commonOptions}
        />
      );
    }
  };

  return (
    <div className="tab-panel space-y-5 px-4 py-4 md:px-6 md:py-6">
      <div className="sec-hd flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
            Insight Engine
          </h2>
          <p className="sec-sub text-[0.63rem] mt-1" style={{ color: "var(--txt-m)" }}>
            Auto-detect patterns · Trends · Anomalies · Correlations · Dataset type detection
          </p>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          <select value={insightTopN} onChange={e => setInsightTopN(e.target.value)} className="inp" style={{ width: "auto", padding: ".4rem .7rem", fontSize: ".75rem", fontWeight: 700 }}>
            <option value="3">3 insights</option>
            <option value="6">6 insights</option>
            <option value="9">9 insights</option>
          </select>
          <button onClick={runInsights} disabled={isRunningInsights} className="bp">
            {isRunningInsights && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>}
            <span className="flex items-center gap-1.5">{isRunningInsights ? 'ANALYSING...' : <><Sparkles size={14} /> RUN INSIGHTS</>}</span>
          </button>
        </div>
      </div>

      {insightError && (
        <div className="p-4 rounded-xl font-mono text-sm text-red-400" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>
          {insightError}
        </div>
      )}

      {insightSchema && ((insightSchema.metrics && insightSchema.metrics.length > 0) || (insightSchema.dimensions && insightSchema.dimensions.length > 0)) && (
        <div className="flex flex-wrap gap-3 items-center">
            <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded" style={{ background: "var(--border)", color: "var(--txt)" }}>Schema Auto-Detected</span>
            {insightSchema.dataset_type && <span className="text-[10px] font-mono px-2 py-1 rounded" style={{ background: "rgba(46,91,255,.1)", color: "var(--accent)" }}>{insightSchema.dataset_type}</span>}
            <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>Metrics: {(insightSchema.metrics || []).join(', ') || 'none'}</span>
            <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>Dimensions: {(insightSchema.dimensions || []).join(', ') || 'none'}</span>
        </div>
      )}

      {insightSummary && (
        <div className="p-5 rounded-2xl flex gap-4" style={{ background: "linear-gradient(135deg,rgba(46,91,255,.05) 0%,rgba(99,102,241,.03) 100%)", border: "1px solid rgba(46,91,255,.15)" }}>
            <div className="text-3xl text-amber-500"><AlertTriangle size={30} /></div>
            <div>
                <p className="text-xs font-bold uppercase tracking-[.15em] mb-1.5" style={{ color: "var(--accent)" }}>AI Summary</p>
                <p className="text-sm leading-relaxed" style={{ color: "var(--txt)" }}>{insightSummary}</p>
            </div>
        </div>
      )}

      {insightCards.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {insightCards.map((ins, i) => {
            const stats = parseInsightStats(ins);
            return (
              <div key={i} className="gc rounded-xl p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-black text-sm leading-tight" style={{ color: "var(--txt)" }}>{ins.title}</p>
                  <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded-full flex-shrink-0" style={insightBadgeStyle(ins.type)}>
                    {ins.type}
                  </span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: "var(--txt-m)" }}>{ins.description}</p>
                <div className="flex items-center gap-2">
                  <span className="sl">Importance</span>
                  <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                    <div className="h-full rounded-full" style={{ width: `${(ins.importance * 100).toFixed(0)}%`, background: "var(--accent)" }}></div>
                  </div>
                  <span className="font-mono text-[10px]" style={{ color: "var(--txt-m)" }}>{(ins.importance * 100).toFixed(0)}%</span>
                </div>

                {ins.chart_data ? (
                  <div style={{ height: "140px", position: "relative" }}>
                    {renderChart(ins)}
                  </div>
                ) : (
                  <div className="mt-1 rounded-xl overflow-hidden ins-stat-wrap">
                    {ins.type === 'anomaly' && (
                      <div className="p-3 space-y-2.5">
                        <div className="flex gap-2">
                          {stats.count !== null && (
                            <div className="ins-stat-box" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.18)", padding: ".5rem", borderRadius: ".5rem", textAlign: "center", flex: 1 }}>
                              <p className="font-black text-xl leading-none text-red-500">{stats.count.toLocaleString()}</p>
                              <p className="text-[9px] font-bold uppercase tracking-widest mt-1" style={{ color: "var(--txt-m)" }}>Anomalies</p>
                            </div>
                          )}
                          {stats.sigma !== null && (
                            <div className="ins-stat-box" style={{ background: "rgba(46,91,255,.08)", border: "1px solid rgba(46,91,255,.18)", padding: ".5rem", borderRadius: ".5rem", textAlign: "center", flex: 1 }}>
                              <p className="font-black text-xl leading-none text-[var(--accent)]">{stats.sigma}σ</p>
                              <p className="text-[9px] font-bold uppercase tracking-widest mt-1" style={{ color: "var(--txt-m)" }}>From Mean</p>
                            </div>
                          )}
                          {stats.value !== null && (
                            <div className="ins-stat-box" style={{ background: "rgba(245,158,11,.08)", border: "1px solid rgba(245,158,11,.18)", padding: ".5rem", borderRadius: ".5rem", textAlign: "center", flex: 1 }}>
                              <p className="font-black text-sm font-mono leading-tight truncate text-yellow-500">{stats.value}</p>
                              <p className="text-[9px] font-bold uppercase tracking-widest mt-1" style={{ color: "var(--txt-m)" }}>Peak</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {ins.type === 'change' && (
                      <div className="p-3 space-y-2">
                        <div className="flex items-stretch justify-center gap-2">
                          {stats.prev !== null && (
                            <div className="ins-stat-box flex-1 text-center" style={{ background: "rgba(255,255,255,.03)", border: "1px solid var(--border)", padding: ".5rem", borderRadius: ".5rem" }}>
                              <p className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Before</p>
                              <p className="font-black text-xs font-mono mt-1 truncate">{Number(stats.prev).toLocaleString()}</p>
                            </div>
                          )}
                          {stats.pct !== null && (
                            <div className="ins-stat-box flex flex-col items-center justify-center flex-1 px-2" style={{ background: "transparent" }}>
                              <p className="font-black text-lg leading-none" style={{ color: parseFloat(stats.pct) >= 0 ? '#1e9902' : '#ef4444' }}>
                                {parseFloat(stats.pct) >= 0 ? '+' : ''}{parseFloat(stats.pct)}%
                              </p>
                            </div>
                          )}
                          {stats.curr !== null && (
                            <div className="ins-stat-box flex-1 text-center" style={{ background: "rgba(30,153,2,.06)", border: "1px solid rgba(30,153,2,.2)", padding: ".5rem", borderRadius: ".5rem" }}>
                              <p className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>After</p>
                              <p className="font-black text-xs font-mono mt-1 truncate" style={{ color: "#1e9902" }}>{Number(stats.curr).toLocaleString()}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!insightCards.length && !isRunningInsights && (
        <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
          <div className="w-20 h-20 rounded-full flex items-center justify-center" style={{ background: "rgba(46,91,255,.08)" }}>
            <Brain size={40} className="text-indigo-500" />
          </div>
          <p className="text-sm max-w-xs" style={{ color: "var(--txt-m)" }}>Click "Run Insights" to automatically detect trends, anomalies, top performers, correlations, and more.</p>
        </div>
      )}
    </div>
  );
}
