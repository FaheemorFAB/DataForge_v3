"use client";

import React from "react";
import {
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sparkles,
  Database,
  Layers,
  ArrowRight,
  X,
  ExternalLink,
} from "lucide-react";

export interface SheetSyncChanges {
  has_changes: boolean;
  old_rows: number;
  new_rows: number;
  rows_delta: number;
  rows_added: number;
  rows_removed: number;
  old_cols: number;
  new_cols: number;
  cols_delta: number;
  added_cols: string[];
  removed_cols: string[];
  values_changed: boolean;
  summary: string;
}

export interface SheetSyncModalState {
  isOpen: boolean;
  result?: {
    ok: boolean;
    profile?: any;
    changes?: SheetSyncChanges;
  };
  error?: string | null;
}

interface SheetSyncModalProps {
  state: SheetSyncModalState | null;
  onClose: () => void;
  onExplore?: () => void;
}

export function SheetSyncModal({ state, onClose, onExplore }: SheetSyncModalProps) {
  if (!state || !state.isOpen) return null;

  const { result, error } = state;
  const changes = result?.changes;
  const hasChanges = changes?.has_changes ?? false;
  const isError = Boolean(error);

  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center p-4 backdrop-blur-md transition-all"
      style={{ background: "rgba(0, 0, 0, 0.65)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden border flex flex-col relative transition-all animate-in fade-in zoom-in-95 duration-150"
        style={{
          background: "var(--surface)",
          borderColor: isError
            ? "rgba(239, 68, 68, 0.35)"
            : hasChanges
            ? "rgba(16, 185, 129, 0.4)"
            : "var(--border)",
          color: "var(--txt)",
          boxShadow: "0 25px 60px -15px rgba(0,0,0,0.6), 0 0 35px var(--glow)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div
          className="px-6 py-5 border-b flex items-center justify-between"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center border shrink-0"
              style={{
                background: isError
                  ? "rgba(239, 68, 68, 0.12)"
                  : hasChanges
                  ? "rgba(16, 185, 129, 0.12)"
                  : "rgba(59, 130, 246, 0.12)",
                borderColor: isError
                  ? "rgba(239, 68, 68, 0.3)"
                  : hasChanges
                  ? "rgba(16, 185, 129, 0.3)"
                  : "rgba(59, 130, 246, 0.3)",
                color: isError ? "#ef4444" : hasChanges ? "#10b981" : "#3b82f6",
              }}
            >
              {isError ? (
                <AlertTriangle size={20} />
              ) : hasChanges ? (
                <Sparkles size={20} />
              ) : (
                <CheckCircle2 size={20} />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold tracking-tight" style={{ color: "var(--txt)" }}>
                  {isError
                    ? "Sync Failed"
                    : hasChanges
                    ? "Google Sheet Synced"
                    : "Already in Sync"}
                </h3>
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-bold font-mono border uppercase tracking-wider"
                  style={{
                    background: isError
                      ? "rgba(239, 68, 68, 0.1)"
                      : hasChanges
                      ? "rgba(16, 185, 129, 0.1)"
                      : "rgba(59, 130, 246, 0.1)",
                    borderColor: isError
                      ? "rgba(239, 68, 68, 0.25)"
                      : hasChanges
                      ? "rgba(16, 185, 129, 0.25)"
                      : "rgba(59, 130, 246, 0.25)",
                    color: isError ? "#ef4444" : hasChanges ? "#10b981" : "#3b82f6",
                  }}
                >
                  {isError ? "Error" : hasChanges ? "Updated" : "Up to date"}
                </span>
              </div>
              <p className="text-xs mt-0.5" style={{ color: "var(--txt-m)" }}>
                {isError
                  ? "Could not refresh dataset from Google Sheets"
                  : hasChanges
                  ? "Live updates were detected and integrated into workspace memory"
                  : "Workspace matches the latest state of your Google Sheet"}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg opacity-60 hover:opacity-100 transition-opacity cursor-pointer"
            style={{ color: "var(--txt-m)" }}
            aria-label="Close dialog"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Case 1: Error */}
          {isError && (
            <div
              className="p-4 rounded-xl border text-xs leading-relaxed space-y-2"
              style={{
                background: "rgba(239, 68, 68, 0.08)",
                borderColor: "rgba(239, 68, 68, 0.25)",
                color: "var(--txt)",
              }}
            >
              <p className="font-semibold text-red-400">Connection Error:</p>
              <p style={{ color: "var(--txt-m)" }}>{error}</p>
              <p className="text-[11px] opacity-80 pt-1">
                Please verify that the Google Sheet link has sharing permissions set to{" "}
                <span className="font-bold underline">Anyone with the link can view</span>.
              </p>
            </div>
          )}

          {/* Case 2: Has Changes */}
          {!isError && hasChanges && changes && (
            <>
              {/* Summary banner */}
              <div
                className="p-3.5 rounded-xl border flex items-center gap-2.5 text-xs font-semibold"
                style={{
                  background: "rgba(16, 185, 129, 0.08)",
                  borderColor: "rgba(16, 185, 129, 0.25)",
                  color: "#10b981",
                }}
              >
                <CheckCircle2 size={16} className="shrink-0" />
                <span>{changes.summary}</span>
              </div>

              {/* 2 Comparison KPI Cards */}
              <div className="grid grid-cols-2 gap-3">
                {/* Rows Card */}
                <div
                  className="p-4 rounded-xl border space-y-2"
                  style={{
                    background: "var(--card)",
                    borderColor: "var(--border)",
                  }}
                >
                  <div className="flex items-center justify-between text-xs" style={{ color: "var(--txt-m)" }}>
                    <span className="font-bold uppercase tracking-wider flex items-center gap-1.5 text-[11px]">
                      <Database size={13} style={{ color: "var(--accent)" }} /> Records
                    </span>
                    {changes.rows_delta !== 0 ? (
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-bold font-mono"
                        style={{
                          background:
                            changes.rows_delta > 0
                              ? "rgba(16, 185, 129, 0.15)"
                              : "rgba(245, 158, 11, 0.15)",
                          color: changes.rows_delta > 0 ? "#10b981" : "#f59e0b",
                        }}
                      >
                        {changes.rows_delta > 0
                          ? `+${changes.rows_delta.toLocaleString()}`
                          : `${changes.rows_delta.toLocaleString()}`}
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono opacity-60">No change</span>
                    )}
                  </div>

                  <div className="flex items-baseline gap-2 font-mono">
                    <span className="text-2xl font-black" style={{ color: "var(--txt)" }}>
                      {changes.new_rows.toLocaleString()}
                    </span>
                    <span className="text-xs line-through opacity-50" style={{ color: "var(--txt-m)" }}>
                      {changes.old_rows.toLocaleString()}
                    </span>
                  </div>

                  <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                    {changes.rows_delta > 0
                      ? `${changes.rows_added.toLocaleString()} newly inserted row${changes.rows_added === 1 ? "" : "s"}`
                      : changes.rows_delta < 0
                      ? `${changes.rows_removed.toLocaleString()} removed row${changes.rows_removed === 1 ? "" : "s"}`
                      : "Row count unchanged"}
                  </p>
                </div>

                {/* Columns Card */}
                <div
                  className="p-4 rounded-xl border space-y-2"
                  style={{
                    background: "var(--card)",
                    borderColor: "var(--border)",
                  }}
                >
                  <div className="flex items-center justify-between text-xs" style={{ color: "var(--txt-m)" }}>
                    <span className="font-bold uppercase tracking-wider flex items-center gap-1.5 text-[11px]">
                      <Layers size={13} style={{ color: "var(--accent)" }} /> Columns
                    </span>
                    {changes.cols_delta !== 0 ? (
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-bold font-mono"
                        style={{
                          background:
                            changes.cols_delta > 0
                              ? "rgba(16, 185, 129, 0.15)"
                              : "rgba(245, 158, 11, 0.15)",
                          color: changes.cols_delta > 0 ? "#10b981" : "#f59e0b",
                        }}
                      >
                        {changes.cols_delta > 0 ? `+${changes.cols_delta}` : `${changes.cols_delta}`}
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono opacity-60">No change</span>
                    )}
                  </div>

                  <div className="flex items-baseline gap-2 font-mono">
                    <span className="text-2xl font-black" style={{ color: "var(--txt)" }}>
                      {changes.new_cols}
                    </span>
                    <span className="text-xs line-through opacity-50" style={{ color: "var(--txt-m)" }}>
                      {changes.old_cols}
                    </span>
                  </div>

                  <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                    {changes.cols_delta > 0
                      ? `${changes.cols_delta} new feature${changes.cols_delta === 1 ? "" : "s"} detected`
                      : changes.cols_delta < 0
                      ? `${Math.abs(changes.cols_delta)} column${Math.abs(changes.cols_delta) === 1 ? "" : "s"} dropped`
                      : "Schema width unchanged"}
                  </p>
                </div>
              </div>

              {/* Added Columns Pill List */}
              {changes.added_cols && changes.added_cols.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[11px] font-semibold" style={{ color: "var(--txt-m)" }}>
                    New Columns Added ({changes.added_cols.length}):
                  </span>
                  <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                    {changes.added_cols.map((colName) => (
                      <span
                        key={colName}
                        className="px-2 py-0.5 rounded-md text-[11px] font-mono font-medium border"
                        style={{
                          background: "var(--card)",
                          borderColor: "rgba(16, 185, 129, 0.3)",
                          color: "#10b981",
                        }}
                      >
                        +{colName}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Cell values updated notice */}
              {changes.values_changed && changes.rows_delta === 0 && changes.cols_delta === 0 && (
                <div
                  className="p-3 rounded-xl border text-xs"
                  style={{
                    background: "var(--card)",
                    borderColor: "var(--border)",
                    color: "var(--txt-m)",
                  }}
                >
                  Cell modifications were detected and updated across existing rows.
                </div>
              )}
            </>
          )}

          {/* Case 3: No Changes (Already in Sync) */}
          {!isError && !hasChanges && (
            <div className="space-y-4 text-center py-2">
              <div
                className="p-5 rounded-2xl border flex flex-col items-center justify-center gap-2"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                }}
              >
                <div
                  className="w-12 h-12 rounded-full flex items-center justify-center border mb-1"
                  style={{
                    background: "rgba(59, 130, 246, 0.1)",
                    borderColor: "rgba(59, 130, 246, 0.25)",
                    color: "#3b82f6",
                  }}
                >
                  <CheckCircle2 size={24} />
                </div>
                <h4 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                  Workspace Is Up to Date
                </h4>
                <p className="text-xs max-w-sm" style={{ color: "var(--txt-m)" }}>
                  We compared the latest rows and columns from your Google Sheet against the workspace memory buffer. No new additions or modifications were found.
                </p>
                <div
                  className="mt-2 px-3 py-1 rounded-full text-xs font-mono font-semibold border flex items-center gap-2"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--txt-m)",
                  }}
                >
                  <span>{(result?.profile?.rows || 0).toLocaleString()} records</span>
                  <span>·</span>
                  <span>{result?.profile?.cols || 0} columns</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="px-6 py-4 border-t flex items-center justify-end gap-2.5"
          style={{ background: "var(--card)", borderColor: "var(--border)" }}
        >
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer hover:opacity-80"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--txt)",
            }}
          >
            Close
          </button>
          {!isError && onExplore && (
            <button
              onClick={() => {
                onClose();
                onExplore();
              }}
              className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-md cursor-pointer hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: "var(--accent)",
                color: "#ffffff",
              }}
            >
              <span>Explore Dataset</span>
              <ArrowRight size={13} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
