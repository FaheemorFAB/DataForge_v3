"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  AlertTriangle,
  Upload,
  FilterX,
  ArrowUp,
  ArrowDown,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
  Search,
  Database,
  Layers,
  Sparkles,
  CheckCircle2,
  Table as TableIcon,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import Spinner from "../../components/ui/Spinner";

export function ExplorerTab() {
  const { profile, cleanProfile, sourceType, isSyncingSheets, syncSheets, uploadId, isLoadingWorkspace } = useWorkspace();
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

  const activeProfile = showClean && cleanProfile ? cleanProfile : profile;

  const reloadData = useCallback(
    async (limitOverride?: number) => {
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
    },
    [rowLimit, showClean, cleanProfile, uploadId, profile?.rows, profile?.cols]
  );

  useEffect(() => {
    reloadData();
  }, [reloadData]);

  useEffect(() => {
    if (cleanProfile) {
      setShowClean(true);
    }
  }, [cleanProfile]);

  const filteredAndSortedRows = useMemo(() => {
    let result = [...allRows];
    if (globalSearch) {
      const q = globalSearch.toLowerCase();
      result = result.filter((row) =>
        row.some((cell: any) => String(cell).toLowerCase().includes(q))
      );
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
        if (typeof vA === "string" && typeof vB === "string") {
          const numA = Number(vA);
          const numB = Number(vB);
          if (!isNaN(numA) && !isNaN(numB)) {
            cA = numA;
            cB = numB;
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
      else {
        setSortCol(null);
        setSortDir(1);
      }
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
    let min = Infinity,
      max = -Infinity,
      sum = 0,
      countNum = 0;

    for (const r of allRows) {
      const v = r[colIdx];
      if (v === null || v === "") {
        nulls++;
        continue;
      }

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
      .map(([val, count]) => ({
        val,
        count,
        pct: ((count / allRows.length) * 100).toFixed(1),
      }));

    setColStats({
      unique: uniqueVals,
      nulls,
      min: countNum > 0 ? (min % 1 === 0 ? min : min.toFixed(2)) : null,
      max: countNum > 0 ? (max % 1 === 0 ? max : max.toFixed(2)) : null,
      mean: countNum > 0 ? (sum / countNum).toFixed(2) : null,
      top,
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
    <div
      className="space-y-6 px-4 py-6 md:px-8 md:py-8 max-w-[1700px] mx-auto transition-colors"
      style={{ color: "var(--txt)" }}
    >
      {/* Alert Banner if reupload is needed */}
      {needsReupload && (
        <div
          className="p-4 rounded-2xl flex items-center justify-between gap-4 border"
          style={{
            background: "rgba(245, 158, 11, 0.1)",
            borderColor: "rgba(245, 158, 11, 0.3)",
            color: "#f59e0b",
          }}
        >
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} className="shrink-0 text-amber-500" />
            <div>
              <p className="font-bold text-sm">Dataset Not Available on Disk</p>
              <p className="text-xs opacity-90 mt-0.5">{reuploadMessage}</p>
            </div>
          </div>
          <a
            href="/"
            className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-md shrink-0"
            style={{
              background: "var(--accent)",
              color: "#ffffff",
            }}
          >
            <Upload size={14} /> Re-upload File
          </a>
        </div>
      )}

      {/* If no dataset loaded yet */}
      {!activeProfile && !needsReupload && (
        (isLoadingWorkspace || loading) ? (
          <div className="py-20 flex items-center justify-center">
            <Spinner
              size="lg"
              variant="brand"
              label="Loading dataset..."
              description="Fetching columns, summary statistics, and grid records..."
            />
          </div>
        ) : (
          <div
            className="p-8 rounded-2xl border text-center flex flex-col items-center justify-center gap-3 shadow-sm my-4"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div
              className="w-12 h-12 rounded-2xl border flex items-center justify-center"
              style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}
            >
              <Database size={22} />
            </div>
            <div>
              <h3 className="text-sm font-bold" style={{ color: "var(--txt)" }}>No Dataset Loaded in Workspace</h3>
              <p className="text-xs max-w-md mx-auto mt-1" style={{ color: "var(--txt-m)" }}>
                Upload your dataset or connect a data source to begin exploring columns, profiles, and data grids.
              </p>
            </div>
            <button
              onClick={() => {
                const btn = document.querySelector('[title="Import a new dataset or connect a data source"]') as HTMLButtonElement;
                if (btn) btn.click();
              }}
              className="mt-2 px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 cursor-pointer shadow-sm hover:scale-[1.02] transition-all"
              style={{ background: "var(--accent)", color: "#fff" }}
            >
              <Upload size={14} />
              <span>Import Dataset</span>
            </button>
          </div>
        )
      )}

      {/* -- 4 High-Impact KPI Telemetry Cards -- */}
      {activeProfile && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-4">

          {/* Card 1: Rows */}
          <div
            className="p-3.5 sm:p-5 rounded-2xl border shadow-sm relative overflow-hidden group transition-all"
            style={{
              background: "var(--card)",
              borderColor: "var(--border)",
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider leading-snug break-words" style={{ color: "var(--txt-m)" }}>
                Total Records
              </span>
              <div
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg border flex items-center justify-center shrink-0"
                style={{
                  background: "var(--glow)",
                  borderColor: "var(--accent)",
                  color: "var(--accent)",
                }}
              >
                <Database size={15} />
              </div>
            </div>
            <p className="text-2xl sm:text-3xl font-black mt-2 tracking-tight font-mono" style={{ color: "var(--txt)" }}>
              {(activeProfile.rows || 0).toLocaleString()}
            </p>
            <div className="flex flex-wrap items-center gap-1 text-[10px] sm:text-xs mt-1.5" style={{ color: "var(--txt-m)" }}>
              <span className="font-bold font-mono" style={{ color: "var(--accent)" }}>
                {loadedRows.toLocaleString()}
              </span>
              <span>rows in buffer</span>
            </div>
          </div>

          {/* Card 2: Columns */}
          <div
            className="p-3.5 sm:p-5 rounded-2xl border shadow-sm relative overflow-hidden group transition-all"
            style={{
              background: "var(--card)",
              borderColor: "var(--border)",
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider leading-snug break-words" style={{ color: "var(--txt-m)" }}>
                Features / Columns
              </span>
              <div
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg border flex items-center justify-center shrink-0"
                style={{
                  background: "var(--glow)",
                  borderColor: "var(--accent)",
                  color: "var(--accent)",
                }}
              >
                <Layers size={15} />
              </div>
            </div>
            <p className="text-2xl sm:text-3xl font-black mt-2 tracking-tight font-mono" style={{ color: "var(--txt)" }}>
              {activeProfile.cols}
            </p>
            <div className="flex flex-wrap items-center gap-1 text-[10px] sm:text-xs mt-1.5" style={{ color: "var(--txt-m)" }}>
              <span className="font-bold" style={{ color: "var(--accent)" }}>
                {activeProfile.numeric} num
              </span>
              <span style={{ color: "var(--txt-f)" }}>·</span>
              <span>{(activeProfile.cols || 0) - (activeProfile.numeric || 0)} cat</span>
            </div>
          </div>

          {/* Card 3: Missing Cells */}
          <div
            className="p-3.5 sm:p-5 rounded-2xl border shadow-sm relative overflow-hidden group transition-all"
            style={{
              background: "var(--card)",
              borderColor: "var(--border)",
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider leading-snug break-words" style={{ color: "var(--txt-m)" }}>
                Missing Values
              </span>
              <div
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg border flex items-center justify-center shrink-0"
                style={{
                  background: "rgba(245, 158, 11, 0.12)",
                  borderColor: "rgba(245, 158, 11, 0.3)",
                  color: "#f59e0b",
                }}
              >
                <AlertTriangle size={15} />
              </div>
            </div>
            <p className="text-2xl sm:text-3xl font-black mt-2 tracking-tight font-mono" style={{ color: "var(--txt)" }}>
              {activeProfile.missing_pct}%
            </p>
            <div className="flex flex-wrap items-center gap-1 text-[10px] sm:text-xs mt-1.5" style={{ color: "var(--txt-m)" }}>
              <span className="font-mono font-bold" style={{ color: "var(--txt)" }}>
                {(activeProfile.missing || 0).toLocaleString()}
              </span>
              <span>empty cells</span>
            </div>
          </div>

          {/* Card 4: Quality Score */}
          <div
            className="p-3.5 sm:p-5 rounded-2xl border shadow-sm relative overflow-hidden group transition-all"
            style={{
              background: "var(--card)",
              borderColor: "var(--border)",
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] sm:text-xs font-bold uppercase tracking-wider leading-snug break-words" style={{ color: "var(--txt-m)" }}>
                Data Completeness
              </span>
              <div
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg border flex items-center justify-center shrink-0"
                style={{
                  background: "var(--glow)",
                  borderColor: "var(--accent)",
                  color: "var(--accent)",
                }}
              >
                <ShieldCheck size={15} />
              </div>
            </div>
            <p className="text-3xl font-black mt-3 tracking-tight font-mono" style={{ color: "var(--accent)" }}>
              {(100 - (activeProfile.missing_pct || 0)).toFixed(1)}%
            </p>
            <div className="flex items-center gap-1.5 text-xs mt-2" style={{ color: "var(--txt-m)" }}>
              <span
                className="w-2 h-2 rounded-full"
                style={{ background: "var(--accent)", boxShadow: "0 0 6px var(--accent)" }}
              />
              <span className="font-semibold" style={{ color: "var(--accent)" }}>Ready for ML &amp; Analysis</span>
            </div>
          </div>
        </div>
      )}

      {/* -- Schema Overview Table -- */}
      {activeProfile?.columns && activeProfile.columns.length > 0 && (
        <div
          className="rounded-2xl border overflow-hidden shadow-sm transition-colors"
          style={{
            background: "var(--card)",
            borderColor: "var(--border)",
          }}
        >
          <div
            className="px-6 py-4 border-b flex items-center justify-between"
            style={{ borderColor: "var(--border)" }}
          >
            <div className="flex items-center gap-2">
              <TableIcon size={16} style={{ color: "var(--accent)" }} />
              <h3 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                Column Schema &amp; Data Types
              </h3>
            </div>
            <span className="text-xs font-mono" style={{ color: "var(--txt-m)" }}>
              {activeProfile.columns.length} columns defined
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead
                className="border-b uppercase tracking-wider font-bold font-mono text-[11px]"
                style={{
                  background: "var(--row-head)",
                  borderColor: "var(--border)",
                  color: "var(--txt-m)",
                }}
              >
                <tr>
                  <th className="sticky left-0 z-10 px-3 sm:px-6 py-2.5 sm:py-3 shadow-[2px_0_5px_rgba(0,0,0,0.1)] sm:shadow-none" style={{ background: "var(--row-head)" }}>Column Name</th>
                  <th className="px-3 sm:px-6 py-2.5 sm:py-3">Data Type</th>
                  <th className="px-3 sm:px-6 py-2.5 sm:py-3">Null %</th>
                  <th className="px-3 sm:px-6 py-2.5 sm:py-3">Completeness</th>
                </tr>
              </thead>
              <tbody className="divide-y font-mono" style={{ borderColor: "var(--border)" }}>
                {activeProfile.columns.map((col: any) => (
                  <tr
                    key={col.name}
                    className="transition-colors"
                    style={{ borderBottomColor: "var(--border)" }}
                  >
                    <td className="px-6 py-3 font-bold" style={{ color: "var(--txt)" }}>
                      {col.name}
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className="px-2 py-0.5 rounded-md border text-[10px]"
                        style={{
                          background: "var(--surface)",
                          borderColor: "var(--border)",
                          color: "var(--txt-m)",
                        }}
                      >
                        {col.dtype}
                      </span>
                    </td>
                    <td className="px-6 py-3" style={{ color: "var(--txt-m)" }}>
                      {col.null_pct}%
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-24 h-2 rounded-full overflow-hidden"
                          style={{ background: "var(--border)" }}
                        >
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${col.quality}%`,
                              background: "var(--accent)",
                            }}
                          />
                        </div>
                        <span className="text-[11px] font-bold" style={{ color: "var(--txt)" }}>
                          {col.quality}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* -- Live Data Grid Explorer -- */}
      {activeProfile && (
        <div className="space-y-4">
          {/* Toolbar */}
          <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-black tracking-tight" style={{ color: "var(--txt)" }}>
              Live Memory Explorer
            </h3>
            <span
              className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold border"
              style={{
                background: "var(--glow)",
                borderColor: "var(--accent)",
                color: "var(--accent)",
              }}
            >
              {filteredAndSortedRows.length.toLocaleString()} rows visible
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Search Input */}
            <div className="relative">
              <Search
                size={13}
                className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: "var(--txt-m)" }}
              />
              <input
                type="text"
                value={globalSearch}
                onChange={(e) => setGlobalSearch(e.target.value)}
                placeholder="Search across all cells..."
                className="w-full sm:w-56 rounded-xl py-1.5 pl-9 pr-3 text-xs focus:outline-none transition-colors border"
                style={{
                  background: "var(--inp-bg)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              />
            </div>

            {/* Row Limit Selector */}
            <select
              value={rowLimit}
              onChange={(e) => setRowLimit(Number(e.target.value))}
              className="rounded-xl px-3 py-1.5 text-xs focus:outline-none border font-semibold"
              style={{
                background: "var(--inp-bg)",
                borderColor: "var(--border)",
                color: "var(--txt)",
              }}
            >
              <option value="200">200 rows</option>
              <option value="500">500 rows</option>
              <option value="1000">1,000 rows</option>
              <option value="2000">2,000 rows</option>
            </select>

            {/* Clean filter toggle */}
            {cleanProfile && (
              <label
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold cursor-pointer"
                style={{
                  background: "var(--inp-bg)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              >
                <input
                  type="checkbox"
                  checked={showClean}
                  onChange={(e) => setShowClean(e.target.checked)}
                  style={{ accentColor: "var(--accent)" }}
                />
                <span>Cleaned View</span>
              </label>
            )}

            {/* Google Sheets Live Sync Button */}
            {sourceType === "sheets" && (
              <button
                onClick={async () => {
                  const res = await syncSheets();
                  if (res?.ok) {
                    await reloadData();
                  }
                }}
                disabled={isSyncingSheets}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all shadow-sm cursor-pointer disabled:opacity-60 hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  background: "rgba(16, 185, 129, 0.12)",
                  borderColor: "rgba(16, 185, 129, 0.35)",
                  color: "#10b981",
                }}
                title="Sync live rows and edits from connected Google Sheet"
              >
                <RefreshCw size={13} className={isSyncingSheets ? "animate-spin" : ""} />
                <span>{isSyncingSheets ? "Syncing..." : "Sync Sheet"}</span>
              </button>
            )}

            {(globalSearch || sortCol) && (
              <button
                onClick={clearAll}
                className="px-3 py-1.5 rounded-xl text-xs font-bold border transition-all flex items-center gap-1 cursor-pointer"
                style={{
                  background: "rgba(239, 68, 68, 0.1)",
                  borderColor: "rgba(239, 68, 68, 0.3)",
                  color: "#ef4444",
                }}
              >
                <FilterX size={13} /> Clear filters
              </button>
            )}
          </div>
        </div>

        {/* Selected Column Quick Stats Panel */}
        {activeCol && colStats && (
          <div
            className="p-4 rounded-2xl border shadow-md space-y-3"
            style={{
              background: "var(--card)",
              borderColor: "var(--accent)",
              boxShadow: "0 0 16px var(--glow)",
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider font-mono" style={{ color: "var(--accent)" }}>
                Column Profile: {activeCol}
              </span>
              <span className="text-[11px]" style={{ color: "var(--txt-m)" }}>Click column header to close</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 pt-1">
              <div>
                <p className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>Distinct</p>
                <p className="text-base font-black font-mono" style={{ color: "var(--txt)" }}>{colStats.unique}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>Nulls</p>
                <p className="text-base font-black font-mono" style={{ color: "var(--txt)" }}>{colStats.nulls}</p>
              </div>
              {colStats.min !== null && (
                <div>
                  <p className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>Min</p>
                  <p className="text-base font-black font-mono" style={{ color: "var(--txt)" }}>{colStats.min}</p>
                </div>
              )}
              {colStats.max !== null && (
                <div>
                  <p className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>Max</p>
                  <p className="text-base font-black font-mono" style={{ color: "var(--txt)" }}>{colStats.max}</p>
                </div>
              )}
              {colStats.mean !== null && (
                <div>
                  <p className="text-[10px] uppercase font-bold" style={{ color: "var(--txt-m)" }}>Mean</p>
                  <p className="text-base font-black font-mono" style={{ color: "var(--txt)" }}>{colStats.mean}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* -- Table Container -- */}
        <div
          className="rounded-2xl border overflow-hidden shadow-sm relative transition-colors"
          style={{
            background: "var(--card)",
            borderColor: "var(--border)",
          }}
        >
          {loading && (
            <div className="absolute inset-0 bg-black/40 z-20 flex flex-col items-center justify-center backdrop-blur-xs">
              <Spinner size="md" variant="brand" label="Updating records..." />
            </div>
          )}

          <div className="overflow-x-auto max-h-[560px]">
            <table className="w-full text-left text-xs border-collapse">
              <thead
                className="border-b sticky top-0 z-10 font-mono text-[11px] uppercase font-bold"
                style={{
                  background: "var(--surface)",
                  borderColor: "var(--border)",
                  color: "var(--txt-m)",
                }}
              >
                <tr>
                  <th className="px-4 py-3.5 text-center w-12" style={{ color: "var(--txt-f)" }}>#</th>
                  {headers.map((h) => (
                    <th
                      key={h}
                      onClick={() => {
                        toggleSort(h);
                        inspectCol(h);
                      }}
                      className="px-4 py-3.5 whitespace-nowrap cursor-pointer transition-colors select-none"
                    >
                      <div className="flex items-center gap-1.5">
                        <span style={{ color: sortCol === h ? "var(--accent)" : "inherit" }}>
                          {h}
                        </span>
                        {sortCol === h ? (
                          <span style={{ color: "var(--accent)" }}>
                            {sortDir === 1 ? <ArrowUp size={12} /> : <ArrowDown size={12} />}
                          </span>
                        ) : (
                          <span className="opacity-30">
                            <ArrowUpDown size={12} />
                          </span>
                        )}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y font-mono" style={{ borderColor: "var(--border)", color: "var(--txt)" }}>
                {pagedRows.map((row, ri) => (
                  <tr
                    key={ri}
                    className="transition-colors hover:opacity-90"
                    style={{ borderBottomColor: "var(--border)" }}
                  >
                    <td className="px-4 py-2.5 text-center text-[10px]" style={{ color: "var(--txt-f)" }}>
                      {currentPage * pageSize + ri + 1}
                    </td>
                    {row.map((cell: any, ci: number) => (
                      <td
                        key={ci}
                        className="px-4 py-2.5 whitespace-nowrap"
                        style={{
                          background: isMatch(cell, headers[ci]) ? "var(--glow)" : "transparent",
                          color: isMatch(cell, headers[ci]) ? "var(--accent)" : "inherit",
                          fontWeight: isMatch(cell, headers[ci]) ? 700 : 400,
                        }}
                      >
                        {cell === null || cell === "" ? (
                          <span style={{ color: "var(--txt-f)" }}>—</span>
                        ) : (
                          String(cell)
                        )}
                      </td>
                    ))}
                  </tr>
                ))}

                {pagedRows.length === 0 && !loading && (
                  <tr>
                    <td
                      colSpan={headers.length + 1}
                      className="text-center py-12 font-mono text-xs"
                      style={{ color: "var(--txt-m)" }}
                    >
                      No records match the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div
            className="px-5 py-3 border-t flex items-center justify-between flex-wrap gap-3 text-xs"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--txt)",
            }}
          >
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
                disabled={currentPage === 0}
                className="p-1.5 rounded-lg border disabled:opacity-40 cursor-pointer"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              >
                <ChevronLeft size={14} />
              </button>
              <span className="font-mono" style={{ color: "var(--txt-m)" }}>
                Page {currentPage + 1} of{" "}
                {Math.max(1, Math.ceil(filteredAndSortedRows.length / pageSize))}
              </span>
              <button
                onClick={() =>
                  setCurrentPage(
                    Math.min(
                      Math.ceil(filteredAndSortedRows.length / pageSize) - 1,
                      currentPage + 1
                    )
                  )
                }
                disabled={
                  currentPage >= Math.ceil(filteredAndSortedRows.length / pageSize) - 1
                }
                className="p-1.5 rounded-lg border disabled:opacity-40 cursor-pointer"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              >
                <ChevronRight size={14} />
              </button>

              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setCurrentPage(0);
                }}
                className="rounded-lg px-2.5 py-1 text-xs focus:outline-none ml-2 border font-semibold"
                style={{
                  background: "var(--inp-bg)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              >
                <option value="25">25 / page</option>
                <option value="50">50 / page</option>
                <option value="100">100 / page</option>
              </select>
            </div>

            {loadedRows < totalRows && (
              <button
                onClick={() =>
                  reloadData(rowLimit < 2000 ? rowLimit + 500 : rowLimit)
                }
                className="text-xs font-bold transition-colors cursor-pointer"
                style={{ color: "var(--accent)" }}
              >
                Load Next 500 Records +
              </button>
            )}
          </div>
        </div>
      </div>
    )}
  </div>
);
}
