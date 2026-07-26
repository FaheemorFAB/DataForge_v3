"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import { AlertTriangle, Upload, FilterX, ArrowUp, ArrowDown, ArrowUpDown, ChevronLeft, ChevronRight, Search } from 'lucide-react';

export function ExplorerTab() {
  const { profile, cleanProfile, sourceType, isSyncingSheets, syncSheets, uploadId } = useWorkspace();
  const [needsReupload, setNeedsReupload] = useState(false);
  const [reuploadMessage, setReuploadMessage] = useState("");

  const [headers, setHeaders] = useState<string[]>([]);
  const [allRows, setAllRows] = useState<any[]>([]);
  const [globalSearch, setGlobalSearch] = useState("");
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<number>(1);
  const [currentPage, setCurrentPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [rowLimit, setRowLimit] = useState<number>(200);
  const [showClean, setShowClean] = useState(false);
  const [activeCol, setActiveCol] = useState<string | null>(null);
  const [colStats, setColStats] = useState<any>(null);
  
  const [totalRows, setTotalRows] = useState(0);
  const [loadedRows, setLoadedRows] = useState(0);
  const [previewOnly, setPreviewOnly] = useState(false);
  
  const [loading, setLoading] = useState(false);

  const activeProfile = (showClean && cleanProfile) ? cleanProfile : profile;

  const reloadData = useCallback(async (limitOverride?: number) => {
    setLoading(true);
    const limit = limitOverride || rowLimit;
    try {
      const url = new URL("/preview", window.location.origin);
      url.searchParams.set("limit", limit.toString());
      if (showClean && cleanProfile) {
        url.searchParams.set("clean", "true");
      }
      if (uploadId) {
        url.searchParams.set("upload_id", uploadId);
      }
      const res = await apiFetch("/preview?" + url.searchParams.toString());
      if (!res.ok) {
        if (res.status === 404) {
          setNeedsReupload(true);
          const e = await res.json();
          setReuploadMessage(e.error || "Dataset file not found.");
        }
        setLoading(false);
        return;
      }
      const data = await res.json();
      setHeaders(data.headers || []);
      setAllRows(data.rows || []);
      setLoadedRows(data.loaded || data.rows?.length || 0);
      setTotalRows(data.total || data.loaded || data.rows?.length || 0);
      setPreviewOnly(!!data.preview_only);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [rowLimit, showClean, cleanProfile, uploadId]);

  useEffect(() => {
    reloadData();
  }, [reloadData]);

  const filteredAndSortedRows = useMemo(() => {
    let result = [...allRows];
    if (globalSearch) {
      const q = globalSearch.toLowerCase();
      result = result.filter(row => row.some((cell: any) => String(cell).toLowerCase().includes(q)));
    }
    if (sortCol && headers.includes(sortCol)) {
      const colIdx = headers.indexOf(sortCol);
      result.sort((a, b) => {
        const vA = a[colIdx];
        const vB = b[colIdx];
        if (vA === vB) return 0;
        if (vA === null || vA === "") return 1;
        if (vB === null || vB === "") return -1;
        
        let cA = vA;
        let cB = vB;
        if (typeof vA === 'string' && typeof vB === 'string') {
          const numA = Number(vA);
          const numB = Number(vB);
          if (!isNaN(numA) && !isNaN(numB)) {
            cA = numA; cB = numB;
          }
        }
        
        if (cA < cB) return -1 * sortDir;
        if (cA > cB) return 1 * sortDir;
        return 0;
      });
    }
    return result;
  }, [allRows, globalSearch, sortCol, sortDir, headers]);

  const pagedRows = useMemo(() => {
    const start = currentPage * pageSize;
    return filteredAndSortedRows.slice(start, start + pageSize);
  }, [filteredAndSortedRows, currentPage, pageSize]);

  const toggleSort = (col: string) => {
    if (sortCol === col) {
      if (sortDir === 1) setSortDir(-1);
      else { setSortCol(null); setSortDir(1); }
    } else {
      setSortCol(col);
      setSortDir(1);
    }
  };

  const inspectCol = (col: string) => {
    if (activeCol === col) {
      setActiveCol(null);
      setColStats(null);
      return;
    }
    setActiveCol(col);
    const colIdx = headers.indexOf(col);
    if (colIdx === -1) return;
    
    let nulls = 0;
    const freqs: Record<string, number> = {};
    let min = Infinity, max = -Infinity, sum = 0, countNum = 0;

    for (const r of allRows) {
      const v = r[colIdx];
      if (v === null || v === "") { nulls++; continue; }
      
      const vStr = String(v);
      freqs[vStr] = (freqs[vStr] || 0) + 1;
      
      const num = Number(v);
      if (!isNaN(num)) {
        if (num < min) min = num;
        if (num > max) max = num;
        sum += num;
        countNum++;
      }
    }
    
    const uniqueVals = Object.keys(freqs).length;
    const top = Object.entries(freqs)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([val, count]) => ({ val, count, pct: ((count / allRows.length) * 100).toFixed(1) }));
      
    setColStats({
      unique: uniqueVals,
      nulls,
      min: countNum > 0 ? (min % 1 === 0 ? min : min.toFixed(2)) : null,
      max: countNum > 0 ? (max % 1 === 0 ? max : max.toFixed(2)) : null,
      mean: countNum > 0 ? (sum / countNum).toFixed(2) : null,
      top
    });
  };

  const clearAll = () => {
    setGlobalSearch("");
    setSortCol(null);
    setSortDir(1);
    setCurrentPage(0);
  };

  const isMatch = (cell: any, header: string) => {
    if (!globalSearch) return false;
    return String(cell).toLowerCase().includes(globalSearch.toLowerCase());
  };

  return (
    <div className="tab-panel space-y-4 px-4 py-4 md:px-6 md:py-6">
      {needsReupload && (
        <div className="p-4 rounded-xl flex items-start justify-between gap-4 flex-wrap" style={{ background: "rgba(245,158,11,.07)", border: "1px solid rgba(245,158,11,.25)" }}>
            <div className="flex items-start gap-3">
                <span style={{ lineHeight: 1, flexShrink: 0 }}><AlertTriangle size={20} className="text-amber-500" /></span>
                <div>
                    <p className="font-bold text-sm" style={{ color: "#f59e0b" }}>Dataset not available on disk</p>
                    <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>{reuploadMessage}</p>
                </div>
            </div>
            <a href="/" className="bp" style={{ background: "#f59e0b" }}><Upload size={14} /> Re-upload File</a>
        </div>
      )}

      {!profile && loading && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                  <div key={`stat-skel-${i}`} className="sc animate-pulse flex flex-col justify-center" style={{ minHeight: "90px" }}>
                      <div className="h-2.5 w-16 rounded mb-3" style={{ background: "var(--border)", opacity: 0.5 }}></div>
                      <div className="h-6 w-20 rounded mb-2.5" style={{ background: "var(--border)", opacity: 0.6 }}></div>
                      <div className="h-2 w-24 rounded" style={{ background: "var(--border)", opacity: 0.4 }}></div>
                  </div>
              ))}
          </div>
      )}

      {profile && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="sc">
                  <p className="sl mb-1">Rows</p>
                  <p className="text-2xl font-black tracking-tighter">{(activeProfile.rows || 0).toLocaleString()}</p>
                  {cleanProfile && showClean && <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>was <span style={{ color: "#1e9902" }}>{profile.rows.toLocaleString()}</span></p>}
              </div>
              <div className="sc">
                  <p className="sl mb-1">Columns</p>
                  <p className="text-2xl font-black tracking-tighter">{activeProfile.cols}</p>
                  <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>{activeProfile.numeric} numeric</p>
              </div>
              <div className="sc">
                  <p className="sl mb-1">Missing</p>
                  <p className="text-2xl font-black tracking-tighter">{activeProfile.missing_pct}%</p>
                  <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>{(activeProfile.missing || 0).toLocaleString()} cells</p>
              </div>
              <div className="sc">
                  <p className="sl mb-1">Quality</p>
                  <p className="text-2xl font-black tracking-tighter" style={{ color: "#1e9902" }}>{(100 - activeProfile.missing_pct).toFixed(1)}%</p>
                  <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>completeness</p>
              </div>
          </div>

          {activeProfile.columns && activeProfile.columns.length > 0 && (
            <div className="gc rounded-2xl overflow-hidden">
                <div className="px-5 py-3 border-b flex items-center justify-between flex-wrap gap-2" style={{ borderColor: "var(--border)" }}>
                    <p className="sl">Column Schema</p>
                    <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px]" style={{ color: "var(--txt-m)" }}>{activeProfile.columns.length} columns</span>
                    </div>
                </div>
                <div className="tbl-scroll">
                    <table className="dt w-full text-left border-collapse">
                        <thead><tr><th>Column</th><th>Type</th><th>Null %</th><th style={{ minWidth: 110 }}>Quality</th></tr></thead>
                        <tbody>
                            {activeProfile.columns.map((col: any) => (
                                <tr key={col.name}>
                                    <td className="font-mono font-bold" style={{ color: "var(--txt)" }}>{col.name}</td>
                                    <td><span className="font-mono text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--border)", color: "var(--txt-m)" }}>{col.dtype.substring(0, 10)}</span></td>
                                    <td className="font-mono">{col.null_pct}%</td>
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <div className="qbg flex-1" style={{ height: 3, width: "100%", background: "var(--border)", borderRadius: 99 }}><div className="qbf" style={{ width: `${col.quality}%`, background: col.quality >= 90 ? "#1e9902" : col.quality >= 70 ? "#f59e0b" : "#ef4444", height: "100%", borderRadius: 99 }}></div></div>
                                            <span className="font-mono text-[10px] w-8 text-right flex-shrink-0" style={{ color: "var(--txt-m)" }}>{col.quality}%</span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
          )}
        </>
      )}

      <div className="space-y-3">
          <div className="expl-toolbar flex items-start justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Live Explorer</h2>
                  <span className="font-mono text-[10px] px-2 py-0.5 rounded-full font-bold" style={{ background: "rgba(46,91,255,.12)", color: "var(--accent)" }}>
                    {filteredAndSortedRows.length.toLocaleString()} filtered · {loadedRows.toLocaleString()} loaded · {totalRows.toLocaleString()} total
                  </span>
                  {sourceType === 'sheets' && (
                      <button onClick={syncSheets} disabled={isSyncingSheets} className={`text-[10px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1.5 transition-all ${isSyncingSheets ? 'opacity-60 cursor-not-allowed' : 'hover:opacity-80'}`} style={{ background: "var(--glow)", color: "var(--accent)", border: "1px solid var(--border)" }}>
                          <svg className={`w-3.5 h-3.5 ${isSyncingSheets ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" /></svg>
                          <span>{isSyncingSheets ? 'Syncing...' : 'Sync Sheet'}</span>
                      </button>
                  )}
              </div>
              <div className="expl-controls flex items-center gap-1 flex-wrap">
                  <div className="relative">
                      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none" style={{ color: "var(--txt-m)" }} size={12} />
                      <input value={globalSearch} onChange={e => setGlobalSearch(e.target.value)} placeholder="Search all columns…" className="pl-7 pr-3 py-1.5 rounded-lg text-[11px] font-medium outline-none w-[180px]" style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }} />
                  </div>
                  {cleanProfile && (
                      <label className="flex items-center gap-1.5 cursor-pointer select-none">
                          <input type="checkbox" checked={showClean} onChange={e => setShowClean(e.target.checked)} style={{ accentColor: "var(--accent)" }} />
                          <span className="font-bold uppercase tracking-widest text-[10px]" style={{ color: "var(--txt-m)" }}>Cleaned</span>
                      </label>
                  )}
                  <select value={rowLimit} onChange={e => setRowLimit(Number(e.target.value))} className="text-[11px] font-bold rounded-lg px-2 py-1.5 outline-none" style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                      <option value="200">200 rows</option>
                      <option value="500">500 rows</option>
                      <option value="1000">1000 rows</option>
                      <option value="2000">2000 rows</option>
                  </select>
                  { (globalSearch || sortCol) && (
                      <button onClick={clearAll} className="text-[10px] font-bold px-2.5 py-1.5 rounded-lg transition-all flex items-center gap-1" style={{ background: "rgba(239,68,68,.1)", color: "#ef4444", border: "1px solid rgba(239,68,68,.25)" }}><FilterX size={12} /> Clear filters</button>
                  )}
              </div>
          </div>

          {activeCol && colStats && (
            <div className="gc rounded-xl p-4 transition-all" style={{ borderLeft: "3px solid var(--accent)" }}>
                <div>
                    <p className="sl mb-1">{activeCol}</p>
                    <p className="text-xs font-bold" style={{ color: "var(--txt-m)" }}>Click a column header to dismiss</p>
                </div>
                <div className="flex flex-wrap gap-5 mt-3">
                    <div><p className="sl">Unique</p><p className="text-lg font-black">{colStats.unique}</p></div>
                    <div><p className="sl">Nulls</p><p className="text-lg font-black">{colStats.nulls}</p></div>
                    {colStats.min !== null && <div><p className="sl">Min</p><p className="text-lg font-black font-mono">{colStats.min}</p></div>}
                    {colStats.max !== null && <div><p className="sl">Max</p><p className="text-lg font-black font-mono">{colStats.max}</p></div>}
                    {colStats.mean !== null && <div><p className="sl">Mean</p><p className="text-lg font-black font-mono">{colStats.mean}</p></div>}
                    <div>
                        <p className="sl mb-1.5">Top values</p>
                        <div className="space-y-1">
                            {colStats.top.map((v: any) => (
                                <div key={v.val} className="flex items-center gap-2">
                                    <div className="h-1.5 rounded-full shrink-0" style={{ background: "var(--accent)", width: `${Math.max(4, Number(v.pct) * 0.8)}px` }}></div>
                                    <span className="text-[10px] font-mono truncate max-w-[120px]" style={{ color: "var(--txt)" }}>{v.val === null || v.val === "null" ? "(null)" : v.val}</span>
                                    <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>{v.count} ({v.pct}%)</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
          )}

          <div className="gc rounded-2xl overflow-hidden relative">
              {loading && pagedRows.length > 0 && (
                <div className="absolute inset-0 bg-black/10 z-10 flex items-center justify-center">
                  <div className="w-6 h-6 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin"></div>
                </div>
              )}
              <div className="overflow-auto tbl-scroll" style={{ maxHeight: 520 }}>
                  <table className="dt w-full min-w-[480px]">
                      <thead>
                          <tr>
                              <th style={{ width: 40, textAlign: "center", color: "var(--txt-f)" }}>#</th>
                              {headers.map(h => (
                                  <th key={h} onClick={() => { toggleSort(h); inspectCol(h); }} className="cursor-pointer select-none whitespace-nowrap" style={{ color: sortCol === h ? "var(--accent)" : "inherit" }}>
                                      <div className="flex items-center gap-1">
                                          <span>{h}</span>
                                          {sortCol === h ? (
                                            <span style={{ color: "var(--accent)" }}>{sortDir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}</span>
                                          ) : (
                                            <span style={{ opacity: 0.2 }}><ArrowUpDown size={12} /></span>
                                          )}
                                      </div>
                                  </th>
                              ))}
                          </tr>
                      </thead>
                      <tbody>
                          {pagedRows.map((row, ri) => (
                              <tr key={ri}>
                                  <td className="text-center font-mono" style={{ color: "var(--txt-f)", fontSize: "0.6rem" }}>{currentPage * pageSize + ri + 1}</td>
                                  {row.map((cell: any, ci: number) => (
                                      <td key={ci} className={isMatch(cell, headers[ci]) ? 'bg-yellow-500/10' : ''} title={cell !== null ? String(cell) : ''}>
                                          {cell === null || cell === '' ? '—' : cell}
                                      </td>
                                  ))}
                              </tr>
                          ))}
                          {pagedRows.length === 0 && !loading && (
                              <tr><td colSpan={Math.max(1, headers.length + 1)} className="text-center py-8 font-mono text-sm" style={{ color: "var(--txt-m)" }}>{totalRows === 0 ? 'No data available' : 'No rows match your filters'}</td></tr>
                          )}
                          {pagedRows.length === 0 && loading && (
                              Array.from({ length: 15 }).map((_, i) => (
                                  <tr key={`skel-${i}`} className="animate-pulse">
                                      <td className="px-2 py-3"><div className="h-3 rounded w-full" style={{ background: "var(--border)", opacity: 0.4 }}></div></td>
                                      {Array.from({ length: Math.max(headers.length, 5) }).map((_, ci) => (
                                          <td key={ci} className="px-2 py-3">
                                              <div className="h-3 rounded w-full" style={{ background: "var(--border)", opacity: 0.4, maxWidth: "120px" }}></div>
                                          </td>
                                      ))}
                                  </tr>
                              ))
                          )}
                      </tbody>
                  </table>
              </div>

              <div className="px-3 py-2.5 border-t flex items-center justify-between flex-wrap gap-2" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
                  <div className="flex items-center gap-2">
                      <button onClick={() => setCurrentPage(Math.max(0, currentPage - 1))} disabled={currentPage === 0} className="ibt" style={{ width: 28, height: 28 }}><ChevronLeft size={16} /></button>
                      <span className="font-mono font-bold text-[10px]" style={{ color: "var(--txt-m)" }}>{currentPage + 1} / {Math.max(1, Math.ceil(filteredAndSortedRows.length / pageSize))}</span>
                      <button onClick={() => setCurrentPage(Math.min(Math.ceil(filteredAndSortedRows.length / pageSize) - 1, currentPage + 1))} disabled={currentPage >= Math.ceil(filteredAndSortedRows.length / pageSize) - 1} className="ibt" style={{ width: 28, height: 28 }}><ChevronRight size={16} /></button>
                      <select value={pageSize} onChange={e => { setPageSize(Number(e.target.value)); setCurrentPage(0); }} className="text-[10px] font-bold rounded px-1.5 py-1 outline-none ml-1" style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                          <option value="25">25/page</option>
                          <option value="50">50/page</option>
                          <option value="100">100/page</option>
                      </select>
                  </div>
                  {loadedRows < totalRows && (
                      <button onClick={() => reloadData(rowLimit < 2000 ? rowLimit + 500 : rowLimit)} className="font-bold uppercase tracking-[.2em] text-[10px] hover:opacity-70 transition-opacity" style={{ color: "var(--accent)" }}>Load More Rows +</button>
                  )}
              </div>
          </div>

          <div className="gc rounded-xl px-4 py-3 flex items-start justify-between gap-3 flex-wrap" style={{ background: "rgba(46,91,255,.04)" }}>
              <div>
                  <p className="text-xs font-bold uppercase tracking-[.18em]" style={{ color: "var(--accent)" }}>Full Dataset Status</p>
                  <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
                      Preview is showing <span className="font-bold" style={{ color: "var(--txt)" }}>{loadedRows.toLocaleString()}</span> of <span className="font-bold" style={{ color: "var(--txt)" }}>{totalRows.toLocaleString()}</span> rows.
                  </p>
              </div>
              {previewOnly && (
                  <span className="bwrn">Preview Sample Only</span>
              )}
          </div>
      </div>
    </div>
  );
}
