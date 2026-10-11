"use client";

import React, { useState, useMemo } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import { 
  Download, AlertTriangle, Sparkles, Sliders, Plus, Trash2, CheckCircle2, 
  FileCode, Eye, Check, X, Shield, Filter, Search, Copy, Terminal, RefreshCw
} from 'lucide-react';

export function CleanerTab() {
  const { uploadId, profile, setCleanProfile, cleanResult, setCleanResult } = useWorkspace();
  const [mode, setMode] = useState<"auto" | "dynamic">("dynamic");
  const [isCleaning, setIsCleaning] = useState(false);
  const [cleanError, setCleanError] = useState("");
  const [alreadyCleanModal, setAlreadyCleanModal] = useState(false);

  // ── Multi-Column Attribute Selection State ─────────────────────────────────
  const [selectedCols, setSelectedCols] = useState<string[]>([]);
  const [colSearch, setColSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<"all" | "numeric" | "text" | "datetime" | "missing">("all");

  // ── Category & Action State ────────────────────────────────────────────────
  const [actionCategory, setActionCategory] = useState<"impute" | "outlier" | "scale" | "encode" | "text" | "cast" | "drop">("impute");

  // Hyperparameters: Imputation
  const [imputeMethod, setImputeMethod] = useState("median");
  const [fillValue, setFillValue] = useState("");
  const [trimPercent, setTrimPercent] = useState(0.10);
  const [interpMethod, setInterpMethod] = useState("linear");
  const [interpOrder, setInterpOrder] = useState(2);
  const [knnNeighbors, setKnnNeighbors] = useState(5);
  const [knnWeights, setKnnWeights] = useState<"uniform" | "distance">("uniform");
  const [miceMaxIter, setMiceMaxIter] = useState(10);
  const [fillLimit, setFillLimit] = useState("");

  // Hyperparameters: Outliers
  const [outlierMethod, setOutlierMethod] = useState("iqr");
  const [multiplierK, setMultiplierK] = useState(1.5);
  const [outlierAction, setOutlierAction] = useState<"clip" | "drop_rows" | "fill_median" | "nullify">("clip");
  const [zscoreThreshold, setZscoreThreshold] = useState(3.0);
  const [zscoreMethod, setZscoreMethod] = useState<"zscore" | "mad">("zscore");
  const [isoContamination, setIsoContamination] = useState(0.05);
  const [isoEstimators, setIsoEstimators] = useState(100);
  const [lowerPercentile, setLowerPercentile] = useState(0.01);
  const [upperPercentile, setUpperPercentile] = useState(0.99);

  // Hyperparameters: Scaling
  const [scalerMethod, setScalerMethod] = useState("robust");
  const [quantileLow, setQuantileLow] = useState(25.0);
  const [quantileHigh, setQuantileHigh] = useState(75.0);
  const [scaleMin, setScaleMin] = useState(0.0);
  const [scaleMax, setScaleMax] = useState(1.0);

  // Hyperparameters: Encoding
  const [encodeMethod, setEncodeMethod] = useState("onehot");
  const [dropFirst, setDropFirst] = useState(false);
  const [minFreq, setMinFreq] = useState(0.0);

  // Hyperparameters: Text & PII
  const [textCase, setTextCase] = useState("trim");
  const [regexPattern, setRegexPattern] = useState("");
  const [regexReplacement, setRegexReplacement] = useState("");
  const [piiMask, setPiiMask] = useState(false);
  const [piiEmail, setPiiEmail] = useState(true);
  const [piiPhone, setPiiPhone] = useState(true);
  const [piiSsn, setPiiSsn] = useState(true);
  const [piiCard, setPiiCard] = useState(true);
  const [fuzzyDedupe, setFuzzyDedupe] = useState(false);
  const [fuzzyThreshold, setFuzzyThreshold] = useState(0.85);

  // Hyperparameters: Type Cast
  const [castType, setCastType] = useState("float");

  // ── Rules Stack & Diff Preview State ───────────────────────────────────────
  const [rules, setRules] = useState<any[]>([]);
  const [diffLoading, setDiffLoading] = useState(false);
  const [diffResult, setDiffResult] = useState<any>(null);
  const [diffError, setDiffError] = useState("");
  const [showCodeModal, setShowCodeModal] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

  const rawColumns = useMemo(() => {
    return profile?.columns || [];
  }, [profile]);

  const filteredColumns = useMemo(() => {
    return rawColumns.filter((colObj: any) => {
      const name = typeof colObj === "string" ? colObj : colObj.name;
      const dtype = (typeof colObj === "object" && colObj.dtype) ? colObj.dtype.toLowerCase() : "";
      const missPct = (typeof colObj === "object" && colObj.null_pct) ? colObj.null_pct : 0;

      // Filter by Search Query
      if (colSearch && !name.toLowerCase().includes(colSearch.toLowerCase())) {
        return false;
      }

      // Filter by Data Type Category
      if (typeFilter === "numeric") {
        return dtype.includes("int") || dtype.includes("float") || dtype.includes("num");
      }
      if (typeFilter === "text") {
        return dtype.includes("str") || dtype.includes("obj") || dtype.includes("cat") || dtype.includes("char");
      }
      if (typeFilter === "datetime") {
        return dtype.includes("date") || dtype.includes("time");
      }
      if (typeFilter === "missing") {
        return missPct > 5.0;
      }
      return true;
    });
  }, [rawColumns, colSearch, typeFilter]);

  const toggleColumnSelection = (colName: string) => {
    setSelectedCols(prev => 
      prev.includes(colName) ? prev.filter(c => c !== colName) : [...prev, colName]
    );
  };

  const selectAllFiltered = () => {
    const names = filteredColumns.map((c: any) => typeof c === "string" ? c : c.name);
    setSelectedCols(Array.from(new Set([...selectedCols, ...names])));
  };

  const clearSelection = () => {
    setSelectedCols([]);
  };

  // ── Construct Current Rule Object ──────────────────────────────────────────
  const buildCurrentRule = () => {
    if (selectedCols.length === 0) return null;
    const rule: any = {
      columns: selectedCols,
      column: selectedCols[0], // fallback for legacy endpoints
      action_type: actionCategory,
    };

    if (actionCategory === "impute") {
      rule.impute_method = imputeMethod;
      if (imputeMethod === "constant") rule.fill_value = fillValue;
      if (imputeMethod === "mean") rule.trim_percent = trimPercent;
      if (imputeMethod === "interpolate") {
        rule.interp_method = interpMethod;
        rule.interp_order = interpOrder;
      }
      if (imputeMethod === "knn") {
        rule.knn_neighbors = knnNeighbors;
        rule.knn_weights = knnWeights;
      }
      if (imputeMethod === "mice") {
        rule.mice_max_iter = miceMaxIter;
      }
      if (["ffill", "bfill"].includes(imputeMethod) && fillLimit) {
        rule.fill_limit = parseInt(fillLimit);
      }
    } else if (actionCategory === "outlier") {
      rule.outlier_method = outlierMethod;
      rule.outlier_action = outlierAction;
      if (outlierMethod === "iqr") rule.multiplier_k = multiplierK;
      if (["zscore", "mad"].includes(outlierMethod)) {
        rule.zscore_threshold = zscoreThreshold;
        rule.zscore_method = zscoreMethod;
      }
      if (outlierMethod === "isolation_forest") {
        rule.iso_contamination = isoContamination;
        rule.iso_estimators = isoEstimators;
      }
      if (outlierMethod === "percentile") {
        rule.lower_percentile = lowerPercentile;
        rule.upper_percentile = upperPercentile;
      }
    } else if (actionCategory === "scale") {
      rule.scaler_method = scalerMethod;
      if (scalerMethod === "robust") {
        rule.quantile_low = quantileLow;
        rule.quantile_high = quantileHigh;
      }
      if (scalerMethod === "minmax") {
        rule.scale_min = scaleMin;
        rule.scale_max = scaleMax;
      }
    } else if (actionCategory === "encode") {
      rule.encode_method = encodeMethod;
      rule.drop_first = dropFirst;
      rule.min_freq = minFreq;
    } else if (actionCategory === "text") {
      rule.text_case = textCase;
      if (regexPattern) {
        rule.regex_pattern = regexPattern;
        rule.regex_replacement = regexReplacement;
      }
      if (piiMask) {
        rule.pii_mask = true;
        const entities: string[] = [];
        if (piiEmail) entities.push("email");
        if (piiPhone) entities.push("phone");
        if (piiSsn) entities.push("ssn");
        if (piiCard) entities.push("credit_card");
        rule.pii_entities = entities;
      }
      if (fuzzyDedupe) {
        rule.fuzzy_dedupe = true;
        rule.fuzzy_threshold = fuzzyThreshold;
      }
    } else if (actionCategory === "cast") {
      rule.cast_type = castType;
    }

    return rule;
  };

  // ── Add Rule to Active DAG Stack ───────────────────────────────────────────
  const addRule = () => {
    const newRule = buildCurrentRule();
    if (!newRule) return;
    setRules(prev => [...prev, newRule]);
    setDiffResult(null);
  };

  const removeRule = (idx: number) => {
    setRules(prev => prev.filter((_, i) => i !== idx));
  };

  // ── Live Diff Preview ──────────────────────────────────────────────────────
  const runPreviewDiff = async () => {
    const candidateRule = buildCurrentRule();
    if (!candidateRule) return;
    setDiffLoading(true);
    setDiffError("");
    setDiffResult(null);
    try {
      const res = await apiFetch("/clean/diff", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, rule: candidateRule }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setDiffError(data.error || "Failed to generate preview diff");
        return;
      }
      setDiffResult(data.diff);
    } catch (err: any) {
      setDiffError(err.message || "Failed to preview diff");
    } finally {
      setDiffLoading(false);
    }
  };

  // ── 1-Click Auto Clean ─────────────────────────────────────────────────────
  const runAutoCleaning = async () => {
    setIsCleaning(true);
    setCleanError("");
    try {
      const res = await apiFetch("/clean", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setCleanError(data.error || "Cleaning failed");
        return;
      }
      setCleanResult(data);
      setCleanProfile(data.clean_profile);

      const missingLog = data.missing_log || [];
      const structActions = data.struct_actions || [];
      const isClean = missingLog.length === 0 && structActions.length === 0;
      if (isClean || (profile && profile.missing_pct === 0)) {
        setAlreadyCleanModal(true);
      }
    } catch (e: any) {
      setCleanError("Network error: " + e.message);
    } finally {
      setIsCleaning(false);
    }
  };

  // ── Run Granular Custom Rules Clean ────────────────────────────────────────
  const runDynamicCleaning = async () => {
    if (rules.length === 0) return;
    setIsCleaning(true);
    setCleanError("");
    try {
      const res = await apiFetch("/clean/dynamic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId, rules }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setCleanError(data.error || "Dynamic cleaning failed");
        return;
      }
      setCleanResult(data);
      setCleanProfile(data.clean_profile);
    } catch (e: any) {
      setCleanError("Network error: " + e.message);
    } finally {
      setIsCleaning(false);
    }
  };

  const copyPythonCode = () => {
    if (cleanResult?.pipeline_script) {
      navigator.clipboard.writeText(cleanResult.pipeline_script);
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 3000);
    }
  };

  return (
    <div className="tab-panel space-y-6 px-4 py-4 md:px-6 md:py-6">
      {/* ── Top Header & Mode Switcher ─────────────────────────────────────── */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
              Enterprise Data Cleaning Studio
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest" style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8" }}>
              v3 Enterprise
            </span>
          </div>
          <p className="text-[0.68rem] mt-1" style={{ color: "var(--txt-m)" }}>
            Multi-column attribute batching · Advanced statistical & ML imputation (KNN / MICE) · Isolation Forest · Robust scalers · PII redaction · Reproducible Python DAG export
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Mode Switcher */}
          <div className="flex p-1 rounded-xl" style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <button onClick={() => setMode("dynamic")} className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
              style={mode === "dynamic" ? { background: "#6366f1", color: "#fff", boxShadow: "0 0 12px rgba(99,102,241,0.3)" } : { color: "var(--txt-m)" }}>
              <Sliders size={13} /> Granular Studio
            </button>
            <button onClick={() => setMode("auto")} className="px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5"
              style={mode === "auto" ? { background: "#6366f1", color: "#fff", boxShadow: "0 0 12px rgba(99,102,241,0.3)" } : { color: "var(--txt-m)" }}>
              <Sparkles size={13} /> 1-Click Auto
            </button>
          </div>

          {cleanResult && (
            <div className="flex gap-2">
              <button onClick={() => setShowCodeModal(true)} className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-all"
                style={{ background: "rgba(99,102,241,0.1)", borderColor: "rgba(99,102,241,0.3)", color: "#818cf8" }}>
                <Terminal size={13} /> Export Script
              </button>
              <a href={`/api/clean/download?upload_id=${uploadId}`} className="bg flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border" style={{ textDecoration: "none" }}><Download size={13} /> CSV</a>
              <a href={`/api/clean/download?format=xlsx&upload_id=${uploadId}`} className="bg flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border" style={{ textDecoration: "none" }}><Download size={13} /> Excel</a>
            </div>
          )}
        </div>
      </div>

      {cleanError && (
        <div className="p-4 rounded-xl space-y-1" style={{ background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.2)" }}>
          <p className="font-bold text-sm text-red-400 flex items-center gap-1.5"><AlertTriangle size={16} /> Cleaning Error</p>
          <p className="font-mono text-xs text-red-400">{cleanError}</p>
        </div>
      )}

      {/* ── MODE 1: 1-Click Automated Cleaner ─────────────────────────────── */}
      {mode === "auto" && (
        <div className="rounded-2xl p-6 space-y-4" style={{ background: "var(--surface)", border: "1px solid rgba(255,255,255,0.07)" }}>
          <div>
            <p className="font-black text-base" style={{ color: "var(--txt)" }}>Automated 1-Click Cleaning</p>
            <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
              Automatically normalizes column names to snake_case, drops &gt;60% missing columns, imputes missing values using distribution heuristics (Mean/Median/Mode), and strips extra whitespace.
            </p>
          </div>
          <button onClick={runAutoCleaning} disabled={isCleaning} className="px-6 py-3 rounded-xl font-bold text-sm text-white flex items-center gap-2"
            style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>
            {isCleaning ? <RefreshCw size={16} className="animate-spin" /> : <Sparkles size={16} />}
            {isCleaning ? "Cleaning Dataset…" : "Run Automated Clean"}
          </button>
        </div>
      )}

      {/* ── MODE 2: Granular Custom Rule Studio ────────────────────────────── */}
      {mode === "dynamic" && (
        <div className="space-y-6">
          <div className="rounded-2xl overflow-hidden border shadow-xl" style={{ background: "var(--surface)", borderColor: "rgba(99,102,241,0.2)" }}>
            
            {/* Step 1: Attribute / Column Selection Matrix */}
            <div className="p-5 border-b" style={{ borderColor: "rgba(255,255,255,0.07)", background: "rgba(99,102,241,0.03)" }}>
              <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg flex items-center justify-center font-black text-xs text-white" style={{ background: "#6366f1" }}>1</div>
                  <span className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>Select Target Attributes</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.05)", color: "var(--txt-m)" }}>
                    {selectedCols.length} of {rawColumns.length} selected
                  </span>
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  {/* Type Filter Pills */}
                  <div className="flex p-0.5 rounded-lg border text-[10px]" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
                    <button onClick={() => setTypeFilter("all")} className={`px-2 py-1 rounded font-bold transition-all ${typeFilter === 'all' ? 'bg-indigo-600 text-white' : 'text-gray-400'}`}>All</button>
                    <button onClick={() => setTypeFilter("numeric")} className={`px-2 py-1 rounded font-bold transition-all ${typeFilter === 'numeric' ? 'bg-indigo-600 text-white' : 'text-gray-400'}`}>Numeric</button>
                    <button onClick={() => setTypeFilter("text")} className={`px-2 py-1 rounded font-bold transition-all ${typeFilter === 'text' ? 'bg-indigo-600 text-white' : 'text-gray-400'}`}>Text</button>
                    <button onClick={() => setTypeFilter("datetime")} className={`px-2 py-1 rounded font-bold transition-all ${typeFilter === 'datetime' ? 'bg-indigo-600 text-white' : 'text-gray-400'}`}>Dates</button>
                    <button onClick={() => setTypeFilter("missing")} className={`px-2 py-1 rounded font-bold transition-all ${typeFilter === 'missing' ? 'bg-indigo-600 text-white' : 'text-gray-400'}`}>Missing &gt;5%</button>
                  </div>

                  <button onClick={selectAllFiltered} className="text-[10px] font-bold px-2 py-1 rounded border hover:bg-white/5" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>Select Filtered</button>
                  <button onClick={clearSelection} className="text-[10px] font-bold px-2 py-1 rounded border text-red-400 hover:bg-red-500/10" style={{ borderColor: "rgba(239,68,68,0.2)" }}>Clear</button>
                </div>
              </div>

              {/* Search Bar */}
              <div className="relative mb-3">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  placeholder="Filter attributes by name..."
                  value={colSearch}
                  onChange={e => setColSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 rounded-xl text-xs font-mono border"
                  style={{ background: "var(--bg)", borderColor: "var(--border)", color: "var(--txt)" }}
                />
              </div>

              {/* Column Pills Grid */}
              <div className="max-h-40 overflow-y-auto p-1 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 no-scrollbar">
                {filteredColumns.map((c: any) => {
                  const name = typeof c === "string" ? c : c.name;
                  const isSelected = selectedCols.includes(name);
                  const dtype = (typeof c === "object" && c.dtype) ? c.dtype : "";
                  const nullPct = (typeof c === "object" && c.null_pct) ? c.null_pct : 0;
                  return (
                    <button
                      key={name}
                      onClick={() => toggleColumnSelection(name)}
                      className={`px-2.5 py-1.5 rounded-xl text-left border flex items-center justify-between gap-1.5 transition-all text-[11px] font-mono ${
                        isSelected 
                          ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-sm" 
                          : "bg-white/[0.02] border-white/[0.06] text-gray-400 hover:border-white/20"
                      }`}
                    >
                      <span className="truncate flex-1">{name}</span>
                      {nullPct > 0 && (
                        <span className="text-[9px] px-1 rounded bg-amber-500/20 text-amber-400 shrink-0">{nullPct}% null</span>
                      )}
                      {isSelected ? <Check size={12} className="shrink-0 text-indigo-400" /> : null}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Step 2: Category & Algorithm Selection */}
            <div className="p-5 border-b" style={{ borderColor: "rgba(255,255,255,0.07)" }}>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center font-black text-xs text-white" style={{ background: "#6366f1" }}>2</div>
                <span className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>Select Cleaning Category & Algorithm</span>
              </div>

              {/* Category Navigation Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-7 gap-1.5 p-1 rounded-xl mb-4 border" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
                {[
                  { id: "impute", label: "Imputation" },
                  { id: "outlier", label: "Outliers" },
                  { id: "scale", label: "Scalers" },
                  { id: "encode", label: "Encoders" },
                  { id: "text", label: "Text / PII" },
                  { id: "cast", label: "Type Cast" },
                  { id: "drop", label: "Drop Cols" },
                ].map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => setActionCategory(cat.id as any)}
                    className={`py-2 px-1 text-[11px] font-bold rounded-lg transition-all text-center ${
                      actionCategory === cat.id ? "bg-indigo-600 text-white shadow-md" : "text-gray-400 hover:text-white"
                    }`}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              {/* Dynamic Hyperparameter Panels */}
              <div className="p-4 rounded-xl border space-y-4" style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.06)" }}>
                
                {/* ── Category: Imputation ───────────────────────────────── */}
                {actionCategory === "impute" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Algorithm</label>
                      <select value={imputeMethod} onChange={e => setImputeMethod(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                        <option value="median">Median (Robust)</option>
                        <option value="mean">Mean (Standard or Trimmed)</option>
                        <option value="knn">KNN Imputer (Multivariate ML)</option>
                        <option value="mice">MICE / Iterative Imputer (High-dim ML)</option>
                        <option value="interpolate">Interpolation (Spline / Polynomial / Linear)</option>
                        <option value="mode">Mode (Most Frequent)</option>
                        <option value="zero">Fill with Zero (0)</option>
                        <option value="constant">Custom Constant</option>
                        <option value="ffill">Forward Fill (ffill)</option>
                        <option value="bfill">Backward Fill (bfill)</option>
                        <option value="drop_rows">Drop Incomplete Rows</option>
                      </select>
                    </div>

                    {imputeMethod === "knn" && (
                      <>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Neighbors (k={knnNeighbors})</label>
                          <input type="range" min={2} max={30} value={knnNeighbors} onChange={e => setKnnNeighbors(parseInt(e.target.value))} className="w-full accent-indigo-500" />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Weights</label>
                          <select value={knnWeights} onChange={e => setKnnWeights(e.target.value as any)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                            <option value="uniform">Uniform</option>
                            <option value="distance">Distance-Weighted</option>
                          </select>
                        </div>
                      </>
                    )}

                    {imputeMethod === "mice" && (
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Max Iterations ({miceMaxIter})</label>
                        <input type="range" min={5} max={50} value={miceMaxIter} onChange={e => setMiceMaxIter(parseInt(e.target.value))} className="w-full accent-indigo-500" />
                      </div>
                    )}

                    {imputeMethod === "mean" && (
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Trim Proportion ({Math.round(trimPercent * 100)}% each tail)</label>
                        <input type="range" min={0} max={0.25} step={0.05} value={trimPercent} onChange={e => setTrimPercent(parseFloat(e.target.value))} className="w-full accent-indigo-500" />
                      </div>
                    )}

                    {imputeMethod === "interpolate" && (
                      <>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Interpolation Type</label>
                          <select value={interpMethod} onChange={e => setInterpMethod(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                            <option value="linear">Linear</option>
                            <option value="polynomial">Polynomial</option>
                            <option value="spline">Spline</option>
                          </select>
                        </div>
                        {["polynomial", "spline"].includes(interpMethod) && (
                          <div className="space-y-1.5">
                            <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Polynomial Order ({interpOrder})</label>
                            <input type="range" min={2} max={5} value={interpOrder} onChange={e => setInterpOrder(parseInt(e.target.value))} className="w-full accent-indigo-500" />
                          </div>
                        )}
                      </>
                    )}

                    {imputeMethod === "constant" && (
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Constant Value</label>
                        <input type="text" placeholder="e.g. Unknown, 0, N/A" value={fillValue} onChange={e => setFillValue(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }} />
                      </div>
                    )}
                  </div>
                )}

                {/* ── Category: Outliers ─────────────────────────────────── */}
                {actionCategory === "outlier" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Detection Algorithm</label>
                      <select value={outlierMethod} onChange={e => setOutlierMethod(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                        <option value="iqr">IQR Fence (Tunable k-Multiplier)</option>
                        <option value="zscore">Z-Score & Robust MAD</option>
                        <option value="isolation_forest">Isolation Forest (Unsupervised ML)</option>
                        <option value="percentile">Percentile Winsorization</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Action on Anomaly</label>
                      <select value={outlierAction} onChange={e => setOutlierAction(e.target.value as any)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                        <option value="clip">Clip to Boundary Values</option>
                        <option value="fill_median">Replace with Median</option>
                        <option value="nullify">Set to NaN / Null</option>
                        <option value="drop_rows">Remove Outlier Rows</option>
                      </select>
                    </div>

                    {outlierMethod === "iqr" && (
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">IQR Multiplier (k={multiplierK})</label>
                        <input type="range" min={1.0} max={3.5} step={0.1} value={multiplierK} onChange={e => setMultiplierK(parseFloat(e.target.value))} className="w-full accent-indigo-500" />
                        <span className="text-[9px] text-gray-500">1.5 = Standard; 3.0 = Extreme Outliers Only</span>
                      </div>
                    )}

                    {outlierMethod === "zscore" && (
                      <>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Method</label>
                          <select value={zscoreMethod} onChange={e => setZscoreMethod(e.target.value as any)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                            <option value="zscore">Standard Z-Score (Mean & Std)</option>
                            <option value="mad">Robust MAD (Median Absolute Deviation)</option>
                          </select>
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Threshold (σ={zscoreThreshold})</label>
                          <input type="range" min={2.0} max={4.5} step={0.1} value={zscoreThreshold} onChange={e => setZscoreThreshold(parseFloat(e.target.value))} className="w-full accent-indigo-500" />
                        </div>
                      </>
                    )}

                    {outlierMethod === "isolation_forest" && (
                      <>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Contamination ({Math.round(isoContamination * 100)}%)</label>
                          <input type="range" min={0.01} max={0.20} step={0.01} value={isoContamination} onChange={e => setIsoContamination(parseFloat(e.target.value))} className="w-full accent-indigo-500" />
                        </div>
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Estimators ({isoEstimators} Trees)</label>
                          <input type="range" min={50} max={300} step={25} value={isoEstimators} onChange={e => setIsoEstimators(parseInt(e.target.value))} className="w-full accent-indigo-500" />
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* ── Category: Scaling ──────────────────────────────────── */}
                {actionCategory === "scale" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Scaling Technique</label>
                      <select value={scalerMethod} onChange={e => setScalerMethod(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                        <option value="robust">RobustScaler (Median & IQR - Outlier Resistant)</option>
                        <option value="standard">StandardScaler (Zero Mean, Unit Variance)</option>
                        <option value="minmax">MinMaxScaler (Bounded Range)</option>
                      </select>
                    </div>

                    {scalerMethod === "robust" && (
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Quantile Bounds ({quantileLow}% – {quantileHigh}%)</label>
                        <div className="flex gap-2">
                          <input type="number" value={quantileLow} onChange={e => setQuantileLow(parseFloat(e.target.value))} className="inp w-1/2" style={{ fontSize: "11px" }} />
                          <input type="number" value={quantileHigh} onChange={e => setQuantileHigh(parseFloat(e.target.value))} className="inp w-1/2" style={{ fontSize: "11px" }} />
                        </div>
                      </div>
                    )}

                    {scalerMethod === "minmax" && (
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Min / Max Range</label>
                        <div className="flex gap-2">
                          <input type="number" value={scaleMin} onChange={e => setScaleMin(parseFloat(e.target.value))} className="inp w-1/2" style={{ fontSize: "11px" }} />
                          <input type="number" value={scaleMax} onChange={e => setScaleMax(parseFloat(e.target.value))} className="inp w-1/2" style={{ fontSize: "11px" }} />
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ── Category: Encoding ─────────────────────────────────── */}
                {actionCategory === "encode" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Encoding Scheme</label>
                      <select value={encodeMethod} onChange={e => setEncodeMethod(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                        <option value="onehot">One-Hot Encoding (pd.get_dummies)</option>
                        <option value="ordinal">Ordinal Encoding (Category Codes)</option>
                      </select>
                    </div>

                    {encodeMethod === "onehot" && (
                      <div className="space-y-1.5 flex flex-col justify-center">
                        <label className="flex items-center gap-2 cursor-pointer text-xs font-bold text-gray-300">
                          <input type="checkbox" checked={dropFirst} onChange={e => setDropFirst(e.target.checked)} className="rounded accent-indigo-500" />
                          Drop First (Avoid Collinearity)
                        </label>
                      </div>
                    )}
                  </div>
                )}

                {/* ── Category: Text / PII ───────────────────────────────── */}
                {actionCategory === "text" && (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Case & Whitespace</label>
                        <select value={textCase} onChange={e => setTextCase(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                          <option value="trim">Trim Whitespace Only</option>
                          <option value="lowercase">Convert to lowercase</option>
                          <option value="uppercase">Convert to UPPERCASE</option>
                          <option value="titlecase">Convert to Title Case</option>
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">RegEx Match Pattern</label>
                        <input type="text" placeholder="e.g. [^a-zA-Z0-9]" value={regexPattern} onChange={e => setRegexPattern(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }} />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">RegEx Replacement</label>
                        <input type="text" placeholder="e.g. _" value={regexReplacement} onChange={e => setRegexReplacement(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }} />
                      </div>

                      <div className="space-y-1.5 flex flex-col justify-center">
                        <label className="flex items-center gap-2 cursor-pointer text-xs font-bold text-gray-300">
                          <input type="checkbox" checked={fuzzyDedupe} onChange={e => setFuzzyDedupe(e.target.checked)} className="rounded accent-indigo-500" />
                          Fuzzy Deduplication ({Math.round(fuzzyThreshold * 100)}%)
                        </label>
                        {fuzzyDedupe && (
                          <input type="range" min={0.65} max={0.98} step={0.01} value={fuzzyThreshold} onChange={e => setFuzzyThreshold(parseFloat(e.target.value))} className="w-full accent-indigo-500 mt-1" />
                        )}
                      </div>
                    </div>

                    {/* PII Redaction Section */}
                    <div className="p-3 rounded-xl border flex items-center justify-between flex-wrap gap-3" style={{ background: "rgba(99,102,241,0.05)", borderColor: "rgba(99,102,241,0.2)" }}>
                      <label className="flex items-center gap-2 cursor-pointer text-xs font-bold text-indigo-300">
                        <Shield size={14} />
                        <input type="checkbox" checked={piiMask} onChange={e => setPiiMask(e.target.checked)} className="rounded accent-indigo-500" />
                        Enable Automated PII Redaction
                      </label>
                      {piiMask && (
                        <div className="flex items-center gap-3 text-xs text-gray-400">
                          <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={piiEmail} onChange={e => setPiiEmail(e.target.checked)} className="accent-indigo-500" /> Email</label>
                          <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={piiPhone} onChange={e => setPiiPhone(e.target.checked)} className="accent-indigo-500" /> Phone</label>
                          <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={piiSsn} onChange={e => setPiiSsn(e.target.checked)} className="accent-indigo-500" /> SSN</label>
                          <label className="flex items-center gap-1.5 cursor-pointer"><input type="checkbox" checked={piiCard} onChange={e => setPiiCard(e.target.checked)} className="accent-indigo-500" /> Credit Card</label>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* ── Category: Type Casting ─────────────────────────────── */}
                {actionCategory === "cast" && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Target Type</label>
                      <select value={castType} onChange={e => setCastType(e.target.value)} className="inp w-full" style={{ fontSize: "11px", padding: "0.5rem" }}>
                        <option value="float">Numeric (Float64)</option>
                        <option value="int">Integer (Int64)</option>
                        <option value="datetime">Datetime (Parsed ISO / Mixed)</option>
                        <option value="string">Text (String)</option>
                        <option value="bool">Boolean</option>
                        <option value="category">Categorical</option>
                      </select>
                    </div>
                  </div>
                )}

                {/* ── Category: Drop Columns ─────────────────────────────── */}
                {actionCategory === "drop" && (
                  <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 font-bold">
                    ⚠️ The selected {selectedCols.length} column(s) will be completely removed from the dataset.
                  </div>
                )}
              </div>

              {/* Action Buttons: Preview Diff & Add to Pipeline */}
              <div className="flex items-center justify-between flex-wrap gap-3 mt-4 pt-3 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <span className="text-[11px] font-mono text-gray-400">
                  Targeting: <strong className="text-indigo-400">{selectedCols.length > 0 ? selectedCols.slice(0, 3).join(", ") + (selectedCols.length > 3 ? ` +${selectedCols.length - 3} more` : "") : "None"}</strong>
                </span>

                <div className="flex items-center gap-2">
                  <button
                    onClick={runPreviewDiff}
                    disabled={selectedCols.length === 0 || diffLoading}
                    className="px-4 py-2 rounded-xl text-xs font-bold border transition-all flex items-center gap-1.5"
                    style={{ borderColor: "rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.03)", color: "var(--txt)" }}
                  >
                    {diffLoading ? <RefreshCw size={13} className="animate-spin text-indigo-400" /> : <Eye size={13} className="text-indigo-400" />}
                    Preview Diff
                  </button>

                  <button
                    onClick={addRule}
                    disabled={selectedCols.length === 0}
                    className="px-5 py-2 rounded-xl text-xs font-bold text-white flex items-center gap-1.5 transition-all shadow-md"
                    style={selectedCols.length === 0 ? { background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.3)", cursor: "not-allowed" } : { background: "#6366f1", boxShadow: "0 0 14px rgba(99,102,241,0.3)" }}
                  >
                    <Plus size={14} /> Add to Pipeline DAG
                  </button>
                </div>
              </div>

              {diffError && (
                <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 font-mono mt-3">
                  {diffError}
                </div>
              )}

              {/* ── Live Diff Preview Card ───────────────────────────────── */}
              {diffResult && (
                <div className="mt-4 p-4 rounded-xl border space-y-3" style={{ background: "rgba(99,102,241,0.03)", borderColor: "rgba(99,102,241,0.2)" }}>
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-black uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                      <Sparkles size={13} /> Simulation Preview for '{diffResult.column}'
                    </p>
                    <button onClick={() => setDiffResult(null)} className="text-gray-500 hover:text-gray-300"><X size={13} /></button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-2.5 rounded-lg border bg-black/20" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                      <span className="text-[10px] uppercase font-bold text-gray-500 block">Missing Values</span>
                      <span className="font-mono text-gray-300">{diffResult.stats_before?.nulls ?? 0} → <strong className="text-emerald-400">{diffResult.stats_after?.nulls ?? 0}</strong></span>
                    </div>
                    {diffResult.stats_before?.mean !== undefined && (
                      <div className="p-2.5 rounded-lg border bg-black/20" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                        <span className="text-[10px] uppercase font-bold text-gray-500 block">Mean (Average)</span>
                        <span className="font-mono text-gray-300">{diffResult.stats_before?.mean} → <strong className="text-indigo-400">{diffResult.stats_after?.mean}</strong></span>
                      </div>
                    )}
                    {diffResult.stats_before?.median !== undefined && (
                      <div className="p-2.5 rounded-lg border bg-black/20" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                        <span className="text-[10px] uppercase font-bold text-gray-500 block">Median</span>
                        <span className="font-mono text-gray-300">{diffResult.stats_before?.median} → <strong className="text-indigo-400">{diffResult.stats_after?.median}</strong></span>
                      </div>
                    )}
                    {diffResult.stats_before?.std !== undefined && (
                      <div className="p-2.5 rounded-lg border bg-black/20" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                        <span className="text-[10px] uppercase font-bold text-gray-500 block">Std Dev</span>
                        <span className="font-mono text-gray-300">{diffResult.stats_before?.std} → <strong className="text-indigo-400">{diffResult.stats_after?.std}</strong></span>
                      </div>
                    )}
                  </div>

                  {/* Sample Rows Diff Table */}
                  {diffResult.sample_diff && diffResult.sample_diff.length > 0 && (
                    <div className="rounded-lg border overflow-hidden mt-2" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                      <table className="w-full text-[11px] font-mono">
                        <thead className="bg-black/30 text-gray-500 uppercase text-[9px]">
                          <tr>
                            <th className="p-2 text-left">Row</th>
                            <th className="p-2 text-left">Before Simulation</th>
                            <th className="p-2 text-left">After Simulation</th>
                            <th className="p-2 text-right">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {diffResult.sample_diff.map((row: any, idx: number) => (
                            <tr key={idx} className="border-t border-white/[0.04]">
                              <td className="p-2 text-gray-500">#{row.row}</td>
                              <td className="p-2 text-gray-300">{row.before}</td>
                              <td className={`p-2 font-bold ${row.changed ? 'text-emerald-400' : 'text-gray-400'}`}>{row.after}</td>
                              <td className="p-2 text-right">
                                {row.changed ? <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">Modified</span> : <span className="text-[9px] text-gray-600">Unchanged</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ── Active Rules DAG Queue ─────────────────────────────────────── */}
          {rules.length > 0 && (
            <div className="rounded-2xl p-5 space-y-4 border shadow-xl" style={{ background: "var(--surface)", borderColor: "rgba(255,255,255,0.07)" }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg flex items-center justify-center font-black text-xs text-white" style={{ background: "#6366f1" }}>3</div>
                  <p className="text-xs font-black uppercase tracking-widest" style={{ color: "var(--txt)" }}>Active Pipeline DAG Stack ({rules.length} Steps)</p>
                </div>
                <button onClick={() => setRules([])} className="text-[10px] font-bold text-red-400 hover:underline flex items-center gap-1"><Trash2 size={12} /> Clear All</button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {rules.map((r, i) => {
                  const targetList = r.columns || [r.column];
                  return (
                    <div key={i} className="rounded-xl p-3 flex items-center justify-between gap-2 border transition-all" style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.07)" }}>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[9px] font-mono px-1 rounded bg-indigo-500/20 text-indigo-300">Step {i + 1}</span>
                          <p className="text-xs font-bold font-mono text-indigo-400 truncate max-w-[150px]">
                            {targetList.join(", ")}
                          </p>
                        </div>
                        <p className="text-[10px] uppercase font-bold mt-1" style={{ color: "var(--txt-m)" }}>
                          {r.action_type === "impute" && `Impute: ${r.impute_method}`}
                          {r.action_type === "outlier" && `Outlier: ${r.outlier_method} (${r.outlier_action})`}
                          {r.action_type === "scale" && `Scale: ${r.scaler_method}`}
                          {r.action_type === "encode" && `Encode: ${r.encode_method}`}
                          {r.action_type === "text" && `Text: ${r.text_case} ${r.pii_mask ? "+ PII" : ""}`}
                          {r.action_type === "cast" && `Cast: ${r.cast_type}`}
                          {r.action_type === "drop" && "Drop Column(s)"}
                        </p>
                      </div>
                      <button onClick={() => removeRule(i)} className="w-6 h-6 rounded flex items-center justify-center text-gray-500 hover:text-red-400 transition-all"><Trash2 size={12} /></button>
                    </div>
                  );
                })}
              </div>

              <button onClick={runDynamicCleaning} disabled={isCleaning} className="w-full py-3.5 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2 transition-all shadow-xl"
                style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 24px rgba(99,102,241,0.3)" }}>
                {isCleaning ? <RefreshCw size={16} className="animate-spin" /> : <CheckCircle2 size={16} />}
                {isCleaning ? "Executing Full Pipeline…" : "Execute Full Cleaning Pipeline"}
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── Results Cards & Audit Log ──────────────────────────────────────── */}
      {cleanResult && (
        <div className="space-y-6 mt-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="gc p-4 rounded-xl">
              <p className="sl">Original Rows</p>
              <p className="text-2xl font-black tracking-tighter mt-1">{cleanResult.stats.original_rows.toLocaleString()}</p>
            </div>
            <div className="gc p-4 rounded-xl">
              <p className="sl">Cleaned Rows</p>
              <p className="text-2xl font-black tracking-tighter mt-1 text-emerald-400">{cleanResult.stats.cleaned_rows.toLocaleString()}</p>
            </div>
            <div className="gc p-4 rounded-xl">
              <p className="sl">Original Cols</p>
              <p className="text-2xl font-black tracking-tighter mt-1">{cleanResult.stats.original_cols}</p>
            </div>
            <div className="gc p-4 rounded-xl">
              <p className="sl">Cleaned Cols</p>
              <p className="text-2xl font-black tracking-tighter mt-1 text-emerald-400">{cleanResult.stats.cleaned_cols}</p>
            </div>
          </div>

          {cleanResult.missing_log && cleanResult.missing_log.length > 0 && (
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: "var(--txt-m)" }}>Cleaning Action Audit Log</h3>
              <div className="gc rounded-xl overflow-hidden">
                <div className="tbl-scroll overflow-x-auto">
                  <table className="dt w-full min-w-[480px]">
                    <thead><tr><th>Target Column</th><th>Type</th><th>Action Performed</th></tr></thead>
                    <tbody>
                      {cleanResult.missing_log.map((row: any, i: number) => (
                        <tr key={i} style={{ borderLeftWidth: "3px", borderLeftStyle: "solid", borderLeftColor: row.type === 'drop' ? '#ef4444' : row.type === 'outlier' ? '#f59e0b' : '#10b981' }}>
                          <td className="font-mono font-bold" style={{ color: "var(--txt)" }}>{row.column}</td>
                          <td><span className="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.05)", color: "var(--txt-m)" }}>{row.type || "clean"}</span></td>
                          <td style={{ color: "var(--txt)" }}>{row.action}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Reproducible Python Script Modal ───────────────────────────────── */}
      {showCodeModal && cleanResult?.pipeline_script && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fadeIn" onClick={() => setShowCodeModal(false)}>
          <div className="w-full max-w-3xl rounded-3xl p-6 flex flex-col shadow-2xl relative overflow-hidden border max-h-[85vh]"
            onClick={e => e.stopPropagation()}
            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}>
            
            <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2">
                <Terminal size={18} className="text-indigo-400" />
                <h3 className="text-base font-black tracking-tight" style={{ color: "var(--txt)" }}>
                  Reproducible Python Cleaning Pipeline
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={copyPythonCode} className="px-3 py-1.5 rounded-xl text-xs font-bold border flex items-center gap-1.5 transition-all"
                  style={{ background: "rgba(99,102,241,0.1)", borderColor: "rgba(99,102,241,0.3)", color: "#818cf8" }}>
                  {copiedCode ? <Check size={13} /> : <Copy size={13} />}
                  {copiedCode ? "Copied!" : "Copy Code"}
                </button>
                <a href={`/api/clean/export-script?upload_id=${uploadId}`} className="px-3 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white flex items-center gap-1.5 shadow-md no-underline">
                  <Download size={13} /> Download .py
                </a>
                <button onClick={() => setShowCodeModal(false)} className="p-1 rounded-lg text-gray-500 hover:text-white"><X size={16} /></button>
              </div>
            </div>

            <p className="text-[11px] text-gray-400 mt-2 mb-3">
              This standalone script encapsulates all transformations applied in this session. Run it on fresh data feeds in your production pipeline.
            </p>

            <div className="flex-1 overflow-auto rounded-xl border bg-black/40 p-4 font-mono text-xs text-gray-300 leading-relaxed no-scrollbar select-all">
              <pre>{cleanResult.pipeline_script}</pre>
            </div>
          </div>
        </div>
      )}

      {/* ── Dataset Already Clean Modal ─────────────────────────────────────── */}
      {alreadyCleanModal && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/65 backdrop-blur-md animate-fadeIn" onClick={() => setAlreadyCleanModal(false)}>
          <div className="w-full max-w-md rounded-3xl p-6 md:p-8 flex flex-col items-center text-center shadow-2xl relative overflow-hidden border"
            onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}>
            
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5 border shadow-lg"
              style={{ background: "rgba(16,185,129,0.12)", borderColor: "rgba(16,185,129,0.3)", color: "#10b981" }}>
              <CheckCircle2 size={34} />
            </div>

            <span className="text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full mb-3" style={{ background: "rgba(16,185,129,0.12)", color: "#10b981", border: "1px solid rgba(16,185,129,0.25)" }}>
              100% Analysis Ready
            </span>

            <h3 className="text-xl font-black tracking-tight mb-2" style={{ color: "var(--txt)" }}>
              Dataset is Already Clean! 🎉
            </h3>

            <p className="text-xs leading-relaxed mb-6" style={{ color: "var(--txt-m)" }}>
              No missing values, duplicate records, or formatting errors were detected in your dataset. Your dataset is already in pristine condition and ready for analysis!
            </p>

            <button onClick={() => setAlreadyCleanModal(false)}
              className="w-full py-3 rounded-xl font-bold text-xs text-white shadow-xl transition-all hover:scale-[1.02]"
              style={{ background: "linear-gradient(135deg,#6366f1,#8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.3)" }}>
              Great, Continue Analysis!
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
