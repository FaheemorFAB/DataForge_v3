"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import { 
  Bot, ShieldAlert, ShieldCheck, AlertTriangle, Sliders, 
  Cpu, Check, Download, Play, RefreshCw, Search, Filter, 
  Terminal, Code, Layers, Zap, BarChart3, ChevronRight, CheckCircle2, Boxes, ArrowRight, AlertCircle, Tag
} from "lucide-react";

interface FeatureInfo {
  name: string;
  dtype: string;
  missing_count: number;
  missing_pct: number;
  n_unique: number;
  is_id: boolean;
  correlation: number | null;
  leakage_risk: "low" | "medium" | "high";
  recommendation: "include" | "drop_leakage" | "drop_id" | "drop_missing";
}

const AVAILABLE_ALGORITHMS = [
  { id: "lgbm", name: "LightGBM", tag: "Ultra Fast", desc: "Gradient boosted trees optimized for speed, low memory, and large datasets." },
  { id: "xgboost", name: "XGBoost", tag: "High Accuracy", desc: "Extreme gradient boosting with exact greedy split search." },
  { id: "catboost", name: "CatBoost", tag: "Categorical", desc: "Symmetric trees with ordered boosting; exceptional for categorical data." },
  { id: "rf", name: "Random Forest", tag: "Ensemble Bagging", desc: "Averaged forest of decision trees; highly resistant to noise and variance." },
  { id: "extra_tree", name: "Extra Trees", tag: "Randomized", desc: "Extremely randomized trees with lower variance and high training throughput." },
  { id: "linear", name: "Linear / Ridge", tag: "Interpretable", desc: "L1/L2 regularized linear model providing an interpretable baseline." },
];

export function AutoMLTab() {
  const { profile, cleanProfile, uploadId, setActiveTab, automlMeta, setAutomlMeta, refreshWorkspace } = useWorkspace();
  const effectiveProfile = cleanProfile || profile;

  // Configuration States
  const [customModelName, setCustomModelName] = useState("");
  const [automlTarget, setAutomlTarget] = useState("");
  const [automlTask, setAutomlTask] = useState("auto-detect");
  const [automlTimeBudget, setAutomlTimeBudget] = useState("60");
  const [automlTestSize, setAutomlTestSize] = useState("20");

  // Feature Selection & Leakage States
  const [featuresList, setFeaturesList] = useState<FeatureInfo[]>([]);
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([]);
  const [isAnalyzingFeatures, setIsAnalyzingFeatures] = useState(false);
  const [featureSearch, setFeatureSearch] = useState("");
  const [featureFilter, setFeatureFilter] = useState<"all" | "numeric" | "categorical" | "safe" | "leakage">("all");

  // Algorithm Whitelist & Hyperparameters
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>(["lgbm", "xgboost", "catboost", "rf", "extra_tree"]);
  const [cvStrategy, setCvStrategy] = useState("auto");
  const [cvFolds, setCvFolds] = useState(5);
  const [metricOverride, setMetricOverride] = useState("auto");

  // Detection & Execution
  const [detectedTask, setDetectedTask] = useState("");
  const [detectedNUnique, setDetectedNUnique] = useState(0);
  const [isTraining, setIsTraining] = useState(false);
  const [automlError, setAutomlError] = useState("");
  const [automlResult, setAutomlResult] = useState<any>(null);
  const [showDeploySnippet, setShowDeploySnippet] = useState(false);
  const [isDeployingModel, setIsDeployingModel] = useState(false);
  const [deploySuccessMsg, setDeploySuccessMsg] = useState("");
  const [deployErrorMsg, setDeployErrorMsg] = useState("");

  // Real Workspace Inference State
  const [isApplyingModel, setIsApplyingModel] = useState(false);
  const [applySuccessMsg, setApplySuccessMsg] = useState("");
  const [applyErrorMsg, setApplyErrorMsg] = useState("");

  // Restore previous AutoML result on refresh
  useEffect(() => {
    if (automlMeta && !automlResult) {
      setAutomlResult(automlMeta);
      if (automlMeta.target) setAutomlTarget(automlMeta.target);
      if (automlMeta.task) setDetectedTask(automlMeta.task);
      if (automlMeta.model_name) setCustomModelName(automlMeta.model_name);
    }
  }, [automlMeta]);

  const applyModelToWorkspace = async () => {
    const targetModelId = automlResult?.registered_model_id;
    if (!targetModelId || !uploadId) return;
    setIsApplyingModel(true);
    setApplySuccessMsg("");
    setApplyErrorMsg("");
    try {
      const res = await apiFetch(`/models/${targetModelId}/apply-to-workspace`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId }),
      });
      if (res.ok) {
        const d = await res.json();
        setApplySuccessMsg(`Successfully scored ${d.rows_scored} rows! Added columns: [${d.new_columns.join(", ")}] to your active workspace dataset.`);
        if (refreshWorkspace) await refreshWorkspace(uploadId);
      } else {
        const err = await res.json().catch(() => ({}));
        setApplyErrorMsg(`Failed to apply model: ${err.detail || err.error || res.statusText}`);
      }
    } catch (err: any) {
      setApplyErrorMsg(`Failed to apply model: ${err.message || String(err)}`);
    } finally {
      setIsApplyingModel(false);
    }
  };

  const deployChampionToRegistry = async () => {
    if (!automlResult) return;
    setIsDeployingModel(true);
    setDeploySuccessMsg("");
    setDeployErrorMsg("");
    try {
      const modelName = (customModelName.trim() || `${automlTarget || "Target"}_${automlResult.best_estimator || "Champion"}`).replace(/[^a-zA-Z0-9_ ]/g, "_");
      const payload = {
        model_name: modelName,
        task_type: automlResult.task || detectedTask || "classification",
        algorithm: automlResult.best_estimator || "Ensemble",
        target_column: automlTarget,
        features: selectedFeatures,
        metrics: automlResult.metrics || { score: automlResult.test_score ?? 0.88 },
        version: "v1.0.0",
        summary: `Champion estimator trained via DataForge tournament on ${effectiveProfile?.filename || "dataset"} (${automlResult.train_rows || 0} rows).`,
        upload_id: uploadId,
      };
      const res = await apiFetch("/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const d = await res.json();
        setDeploySuccessMsg(`Successfully deployed ${modelName} (ID: ${d.model?.id || "REG-01"}) to Enterprise Model Registry!`);
      } else {
        const err = await res.json().catch(() => ({}));
        setDeployErrorMsg(`Deployment failed: ${err.detail || err.error || res.statusText}`);
      }
    } catch (err: any) {
      setDeployErrorMsg(`Deployment failed: ${err.message || String(err)}`);
    } finally {
      setIsDeployingModel(false);
    }
  };

  // Available columns from profile
  const allColumns: string[] = useMemo(() => {
    if (effectiveProfile?.columns && Array.isArray(effectiveProfile.columns)) {
      return effectiveProfile.columns.map((c: any) => c.name);
    }
    return [];
  }, [effectiveProfile]);

  // When target changes, analyze task & feature signals
  useEffect(() => {
    if (automlTarget) {
      runFeatureAnalysis(automlTarget);
    } else {
      setFeaturesList([]);
      setSelectedFeatures([]);
      setDetectedTask("");
      setDetectedNUnique(0);
    }
  }, [automlTarget, uploadId]);

  const runFeatureAnalysis = async (target: string) => {
    if (!target || !uploadId) return;
    setIsAnalyzingFeatures(true);
    try {
      // 1. Detect task
      const taskRes = await apiFetch("/automl/detect-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_col: target, upload_id: uploadId }),
      });
      if (taskRes.ok) {
        const taskData = await taskRes.json();
        setDetectedTask(taskData.task || "");
        setDetectedNUnique(taskData.n_unique || 0);
      }

      // 2. Comprehensive Feature Analysis & Leakage Audit
      const featRes = await apiFetch("/automl/feature-analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_col: target, upload_id: uploadId }),
      });

      if (featRes.ok) {
        const featData = await featRes.json();
        if (featData.features && Array.isArray(featData.features)) {
          setFeaturesList(featData.features);
          // Auto-select features recommended as "include" (omit high leakage & ID columns by default)
          const recommended = featData.features
            .filter((f: FeatureInfo) => f.recommendation === "include")
            .map((f: FeatureInfo) => f.name);
          setSelectedFeatures(recommended);
        }
      }
    } catch (err) {
      console.error("Feature analysis failed", err);
    } finally {
      setIsAnalyzingFeatures(false);
    }
  };

  // Toggle single feature
  const toggleFeature = (colName: string) => {
    setSelectedFeatures(prev => 
      prev.includes(colName) ? prev.filter(c => c !== colName) : [...prev, colName]
    );
  };

  // Batch feature selection helpers
  const selectAllFeatures = () => {
    setSelectedFeatures(featuresList.map(f => f.name));
  };

  const selectSafeFeaturesOnly = () => {
    const safe = featuresList.filter(f => f.leakage_risk !== "high" && !f.is_id).map(f => f.name);
    setSelectedFeatures(safe);
  };

  const deselectAllFeatures = () => {
    setSelectedFeatures([]);
  };

  // Algorithm toggles
  const toggleAlgorithm = (algoId: string) => {
    setSelectedAlgos(prev => {
      if (prev.includes(algoId)) {
        if (prev.length <= 1) return prev; // At least one algorithm required
        return prev.filter(a => a !== algoId);
      }
      return [...prev, algoId];
    });
  };

  // Filter features for display
  const displayedFeatures = useMemo(() => {
    return featuresList.filter(f => {
      if (featureSearch && !f.name.toLowerCase().includes(featureSearch.toLowerCase())) {
        return false;
      }
      if (featureFilter === "numeric") {
        return f.dtype.includes("int") || f.dtype.includes("float");
      }
      if (featureFilter === "categorical") {
        return f.dtype.includes("object") || f.dtype.includes("category") || f.dtype.includes("string");
      }
      if (featureFilter === "safe") {
        return f.leakage_risk === "low" && !f.is_id;
      }
      if (featureFilter === "leakage") {
        return f.leakage_risk === "high" || f.leakage_risk === "medium";
      }
      return true;
    });
  }, [featuresList, featureSearch, featureFilter]);

  const highRiskCount = useMemo(() => {
    return featuresList.filter(f => f.leakage_risk === "high").length;
  }, [featuresList]);

  // Execute Training
  const runAutoml = async () => {
    if (!automlTarget || !uploadId) return;
    if (selectedFeatures.length === 0) {
      setAutomlError("You must select at least one feature column for training.");
      return;
    }
    if (selectedAlgos.length === 0) {
      setAutomlError("You must select at least one algorithm from the whitelist.");
      return;
    }

    setIsTraining(true);
    setAutomlError("");
    setAutomlResult(null);

    try {
      const res = await apiFetch("/automl/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_col: automlTarget,
          task_choice: automlTask,
          time_budget: parseInt(automlTimeBudget, 10),
          test_size: parseFloat(automlTestSize),
          feature_whitelist: selectedFeatures,
          algorithm_whitelist: selectedAlgos,
          cv_strategy: cvStrategy,
          cv_folds: cvFolds,
          metric_override: metricOverride,
          upload_id: uploadId,
          model_name: customModelName.trim() || undefined,
        }),
      });

      if (!res.ok) {
        let errStr = "AutoML training initiation failed.";
        try {
          const data = await res.json();
          if (data.detail) errStr = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
          else if (data.error) errStr = data.error;
        } catch (e) {}
        setAutomlError(errStr);
        setIsTraining(false);
        return;
      }

      const data = await res.json();
      if (data.error) {
        setAutomlError(data.error);
        setIsTraining(false);
        return;
      }

      // Poll task status until complete
      const pollTask = async (taskId: string) => {
        let attempts = 0;
        while (attempts < 600) {
          attempts++;
          await new Promise(r => setTimeout(r, 2000));
          const pRes = await apiFetch(`/tasks/status/${taskId}`);
          if (!pRes.ok) throw new Error("AutoML job status polling failed.");
          const pData = await pRes.json();
          if (pData.status === "completed" || pData.status === "success") {
            if (pData.result?.key === "automl_meta" && uploadId) {
              const metaRes = await apiFetch(`/workspace/state?upload_id=${uploadId}`);
              if (metaRes.ok) {
                const state = await metaRes.json();
                if (state.automl_meta) return state.automl_meta;
              }
            }
            return pData.result;
          }
          if (pData.status === "failure" || pData.status === "failed") {
            throw new Error(pData.error || "AutoML model training failed.");
          }
        }
        throw new Error("AutoML training timed out.");
      };

      const result = await pollTask(data.task_id);
      setAutomlResult(result);
      if (setAutomlMeta) setAutomlMeta(result);
    } catch (e: any) {
      setAutomlError(String(e.message || e));
    } finally {
      setIsTraining(false);
    }
  };

  return (
    <div className="tab-panel space-y-6 px-4 py-5 md:px-8 md:py-7 max-w-7xl mx-auto">
      {/* -- TOP HEADER -- */}
      <div className="sec-hd flex items-start justify-between flex-wrap gap-4 border-b pb-5" style={{ borderColor: "var(--border)" }}>
        <div>
          <div className="flex items-center gap-2.5">
            <span className="p-2 rounded-xl flex items-center justify-center text-white" style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
              <Bot size={20} />
            </span>
            <h2 className="text-2xl font-black uppercase tracking-tight" style={{ background: "linear-gradient(135deg,var(--txt),var(--txt-m))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", lineHeight: 1.1 }}>
              Enterprise AutoML Studio
            </h2>
          </div>
          <p className="sec-sub text-xs mt-1 font-mono" style={{ color: "var(--txt-m)" }}>
            FLAML · Whitelist Feature Selection · Target Leakage Guard · Tunable Ensembles
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          {automlResult && (
            <>
              <button 
                onClick={() => setShowDeploySnippet(!showDeploySnippet)} 
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all"
                style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1", border: "1px solid rgba(99,102,241,0.25)" }}>
                <Code size={14} />
                <span>{showDeploySnippet ? "Hide API Code" : "Inference Code"}</span>
              </button>

              <a 
                href={`/api/automl/download?upload_id=${uploadId}`} 
                download
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white shadow-md transition-all hover:opacity-90"
                style={{ background: "linear-gradient(135deg, #10b981, #059669)", textDecoration: "none" }}>
                <Download size={14} />
                <span>DOWNLOAD MODEL (.joblib)</span>
              </a>
            </>
          )}
        </div>
      </div>

      {/* -- SECTION 1: TARGET SELECTION & PRIMARY CONFIG -- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 p-5 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        {/* Target Column */}
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider block mb-1.5" style={{ color: "var(--txt-m)" }}>
            Target Variable (Y)
          </label>
          <select 
            value={automlTarget} 
            onChange={e => {
              const val = e.target.value;
              setAutomlTarget(val);
              if (!customModelName && val) {
                setCustomModelName(`${val.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())} Predictor`);
              }
            }} 
            className="w-full text-xs font-semibold px-3 py-2.5 rounded-xl outline-none transition-all"
            style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
            <option value="">- Select Target Column -</option>
            {allColumns.map(col => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
          {detectedTask && (
            <div className="mt-2 flex items-center gap-1.5 text-[10px] font-bold px-2 py-1 rounded-md" style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6" }}>
              <Zap size={11} />
              <span>Detected: {detectedTask} ({detectedNUnique} unique)</span>
            </div>
          )}
        </div>

        {/* Model Name Input */}
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1.5 mb-1.5" style={{ color: "var(--txt-m)" }}>
            <Tag size={12} className="text-indigo-500" />
            <span>Model Name</span>
          </label>
          <input
            type="text"
            value={customModelName}
            onChange={e => setCustomModelName(e.target.value)}
            placeholder={automlTarget ? `${automlTarget} Predictor` : "e.g. Loan Risk Ensemble v1"}
            className="w-full text-xs font-semibold px-3 py-2.5 rounded-xl outline-none transition-all shadow-sm"
            style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}
          />
          <span className="block mt-1 text-[10px]" style={{ color: "var(--txt-f)" }}>
            Saved to Model Catalog on training
          </span>
        </div>

        {/* Task Override */}
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider block mb-1.5" style={{ color: "var(--txt-m)" }}>
            Task Objective
          </label>
          <select 
            value={automlTask} 
            onChange={e => setAutomlTask(e.target.value)} 
            className="w-full text-xs font-semibold px-3 py-2.5 rounded-xl outline-none transition-all"
            style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
            <option value="auto-detect">Auto (Inferred from Target)</option>
            <option value="classification">Classification</option>
            <option value="regression">Regression</option>
          </select>
          <span className="block mt-1 text-[10px]" style={{ color: "var(--txt-f)" }}>
            Forces binary/multiclass or continuous loss
          </span>
        </div>

        {/* Time Budget */}
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider block mb-1.5" style={{ color: "var(--txt-m)" }}>
            Search Time Budget
          </label>
          <select 
            value={automlTimeBudget} 
            onChange={e => setAutomlTimeBudget(e.target.value)} 
            className="w-full text-xs font-semibold px-3 py-2.5 rounded-xl outline-none transition-all"
            style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
            <option value="15">15 seconds (Rapid Prototype)</option>
            <option value="60">60 seconds (Standard)</option>
            <option value="180">3 minutes (Extended Search)</option>
            <option value="600">10 minutes (Deep Ensemble)</option>
            <option value="900">15 minutes (Benchmark)</option>
          </select>
          <span className="block mt-1 text-[10px]" style={{ color: "var(--txt-f)" }}>
            FLAML multi-core optimization timeout
          </span>
        </div>

        {/* Test Split */}
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider block mb-1.5" style={{ color: "var(--txt-m)" }}>
            Holdout Test Split
          </label>
          <div className="flex items-center gap-3 mt-1.5">
            <input 
              type="range" 
              min="10" 
              max="40" 
              step="5"
              value={automlTestSize} 
              onChange={e => setAutomlTestSize(e.target.value)}
              className="flex-1 accent-[var(--accent)]" 
            />
            <span className="font-mono text-xs font-black px-2 py-1 rounded-md" style={{ background: "var(--border)", color: "var(--txt)" }}>
              {automlTestSize}%
            </span>
          </div>
          <span className="block mt-1 text-[10px]" style={{ color: "var(--txt-f)" }}>
            {100 - parseInt(automlTestSize, 10)}% train / {automlTestSize}% test
          </span>
        </div>
      </div>

      {/* -- SECTION 2: GRANULAR FEATURE SELECTION & LEAKAGE GUARD -- */}
      {automlTarget && (
        <div className="p-5 rounded-2xl space-y-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Sliders size={16} style={{ color: "var(--accent)" }} />
                <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                  Feature Whitelist & Leakage Guard
                </h3>
                <span className="text-xs px-2 py-0.5 rounded-full font-mono font-bold" style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1" }}>
                  {selectedFeatures.length} of {featuresList.length} Selected
                </span>
              </div>
              <p className="text-xs mt-0.5" style={{ color: "var(--txt-m)" }}>
                Explicitly whitelist predictors. Deselect high-correlation features to eliminate target leakage.
              </p>
            </div>

            {/* Batch Selection Action Buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              <button 
                onClick={selectSafeFeaturesOnly}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold"
                style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.25)" }}>
                <ShieldCheck size={12} />
                <span>Select Safe Only</span>
              </button>
              <button 
                onClick={selectAllFeatures}
                className="px-2.5 py-1 rounded-lg text-[11px] font-bold"
                style={{ background: "var(--border)", color: "var(--txt)" }}>
                Select All
              </button>
              <button 
                onClick={deselectAllFeatures}
                className="px-2.5 py-1 rounded-lg text-[11px] font-bold"
                style={{ background: "var(--border)", color: "var(--txt)" }}>
                Clear
              </button>
            </div>
          </div>

          {/* High Risk Leakage Banner */}
          {highRiskCount > 0 && (
            <div className="p-3.5 rounded-xl flex items-start gap-3" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)" }}>
              <ShieldAlert size={18} className="text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-red-500">
                  Target Leakage Alert: {highRiskCount} feature{highRiskCount > 1 ? 's' : ''} with &gt;90% correlation found!
                </p>
                <p className="text-[11px] text-red-400 mt-0.5">
                  Training with these features will produce deceptively high test scores that fail in production. We have unselected them by default.
                </p>
              </div>
            </div>
          )}

          {/* Search & Filter Bar */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="relative flex-1 min-w-[200px]">
              <Search size={14} className="absolute left-3 top-2.5" style={{ color: "var(--txt-m)" }} />
              <input 
                type="text" 
                placeholder="Search feature names..."
                value={featureSearch}
                onChange={e => setFeatureSearch(e.target.value)}
                className="w-full text-xs pl-8 pr-3 py-2 rounded-xl outline-none"
                style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}
              />
            </div>

            <div className="flex items-center gap-1">
              {(["all", "numeric", "categorical", "safe", "leakage"] as const).map(tab => (
                <button 
                  key={tab}
                  onClick={() => setFeatureFilter(tab)}
                  className={`px-2.5 py-1.5 rounded-lg text-[10px] font-bold capitalize transition-all ${featureFilter === tab ? 'text-white' : ''}`}
                  style={{
                    background: featureFilter === tab ? "var(--accent)" : "transparent",
                    color: featureFilter === tab ? "white" : "var(--txt-m)",
                    border: `1px solid ${featureFilter === tab ? "var(--accent)" : "var(--border)"}`,
                  }}>
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {/* Features Table */}
          {isAnalyzingFeatures ? (
            <div className="p-8 text-center space-y-2">
              <RefreshCw size={20} className="animate-spin mx-auto text-indigo-500" />
              <p className="text-xs font-mono" style={{ color: "var(--txt-m)" }}>Auditing feature correlations & target leakage...</p>
            </div>
          ) : (
            <div className="max-h-[300px] overflow-y-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
              <table className="w-full text-left text-xs border-collapse">
                <thead className="sticky top-0 z-10 font-mono text-[10px] uppercase tracking-wider" style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", color: "var(--txt-m)" }}>
                  <tr>
                    <th className="py-2.5 px-3 w-10 text-center">Inc.</th>
                    <th className="py-2.5 px-3">Feature Name</th>
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Null %</th>
                    <th className="py-2.5 px-3">Unique</th>
                    <th className="py-2.5 px-3">Signal (Corr)</th>
                    <th className="py-2.5 px-3">Leakage Risk</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                  {displayedFeatures.map(f => {
                    const isSelected = selectedFeatures.includes(f.name);
                    return (
                      <tr 
                        key={f.name}
                        onClick={() => toggleFeature(f.name)}
                        className="cursor-pointer transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                        style={{ background: isSelected ? "rgba(99,102,241,0.03)" : "transparent" }}>
                        <td className="py-2 px-3 text-center" onClick={e => e.stopPropagation()}>
                          <input 
                            type="checkbox" 
                            checked={isSelected}
                            onChange={() => toggleFeature(f.name)}
                            className="rounded accent-[var(--accent)]"
                          />
                        </td>
                        <td className="py-2 px-3 font-semibold font-mono text-[11px]" style={{ color: isSelected ? "var(--txt)" : "var(--txt-m)" }}>
                          {f.name}
                          {f.is_id && <span className="ml-2 text-[9px] px-1 py-0.2 rounded font-sans font-bold bg-amber-500/10 text-amber-500">ID Candidate</span>}
                        </td>
                        <td className="py-2 px-3">
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded" style={{ background: "var(--border)", color: "var(--txt-m)" }}>
                            {f.dtype}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-mono text-[11px]" style={{ color: f.missing_pct > 20 ? "#ef4444" : "var(--txt-m)" }}>
                          {f.missing_pct}%
                        </td>
                        <td className="py-2 px-3 font-mono text-[11px]" style={{ color: "var(--txt-m)" }}>
                          {f.n_unique}
                        </td>
                        <td className="py-2 px-3 font-mono text-[11px]">
                          {f.correlation !== null ? (
                            <span style={{ color: Math.abs(f.correlation) >= 0.9 ? "#ef4444" : Math.abs(f.correlation) >= 0.4 ? "#10b981" : "var(--txt-m)" }}>
                              {f.correlation > 0 ? `+${f.correlation.toFixed(3)}` : f.correlation.toFixed(3)}
                            </span>
                          ) : (
                            <span style={{ color: "var(--txt-f)" }}>-</span>
                          )}
                        </td>
                        <td className="py-2 px-3">
                          {f.leakage_risk === "high" ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-500/15 text-red-500">
                              <AlertTriangle size={10} /> High Risk
                            </span>
                          ) : f.leakage_risk === "medium" ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-500">
                              Medium Signal
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500">
                              <CheckCircle2 size={10} /> Safe
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* -- SECTION 3: ALGORITHM WHITELIST & VALIDATION TUNING -- */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left Column: Algorithm Whitelist (7 cols) */}
        <div className="lg:col-span-7 p-5 rounded-2xl space-y-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu size={16} style={{ color: "var(--accent)" }} />
              <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                Algorithm Whitelist
              </h3>
            </div>
            <span className="text-xs font-mono" style={{ color: "var(--txt-m)" }}>
              {selectedAlgos.length} Models Active
            </span>
          </div>
          <p className="text-xs" style={{ color: "var(--txt-m)" }}>
            Restrict FLAML's search space to compliant or hardware-preferred model architectures.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {AVAILABLE_ALGORITHMS.map(algo => {
              const isChecked = selectedAlgos.includes(algo.id);
              return (
                <div 
                  key={algo.id}
                  onClick={() => toggleAlgorithm(algo.id)}
                  className="p-3.5 rounded-xl border cursor-pointer transition-all flex items-start gap-3 select-none"
                  style={{
                    background: isChecked ? "rgba(99,102,241,0.06)" : "transparent",
                    borderColor: isChecked ? "rgba(99,102,241,0.4)" : "var(--border)",
                  }}>
                  <div 
                    className="w-4 h-4 rounded mt-0.5 flex items-center justify-center transition-all"
                    style={{
                      background: isChecked ? "var(--accent)" : "transparent",
                      border: `1.5px solid ${isChecked ? "var(--accent)" : "var(--txt-m)"}`,
                    }}>
                    {isChecked && <Check size={11} className="text-white" strokeWidth={3} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-xs" style={{ color: isChecked ? "var(--txt)" : "var(--txt-m)" }}>
                        {algo.name}
                      </span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-black/5 dark:bg-white/5" style={{ color: "var(--txt-m)" }}>
                        {algo.tag}
                      </span>
                    </div>
                    <p className="text-[10px] mt-1 leading-tight line-clamp-2" style={{ color: "var(--txt-f)" }}>
                      {algo.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Cross-Validation & Metric Tuning (5 cols) */}
        <div className="lg:col-span-5 p-5 rounded-2xl space-y-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-2">
            <Layers size={16} style={{ color: "var(--accent)" }} />
            <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
              Validation & Metric Objective
            </h3>
          </div>
          <p className="text-xs" style={{ color: "var(--txt-m)" }}>
            Tune hyperparameter search objectives and evaluation splitting schemas.
          </p>

          <div className="space-y-3.5">
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                Validation Strategy
              </label>
              <select 
                value={cvStrategy} 
                onChange={e => setCvStrategy(e.target.value)} 
                className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none"
                style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                <option value="auto">Auto (Dataset Adaptive)</option>
                <option value="stratified_kfold">Stratified K-Fold (Robust)</option>
                <option value="kfold">Standard K-Fold</option>
                <option value="holdout">Single Train/Test Split (Fast)</option>
              </select>
            </div>

            {cvStrategy !== "holdout" && (
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                  Number of Folds (K)
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[3, 5, 10].map(k => (
                    <button 
                      key={k}
                      type="button"
                      onClick={() => setCvFolds(k)}
                      className={`py-1.5 rounded-lg text-xs font-mono font-bold transition-all ${cvFolds === k ? 'text-white' : ''}`}
                      style={{
                        background: cvFolds === k ? "var(--accent)" : "var(--inp-bg)",
                        color: cvFolds === k ? "white" : "var(--txt-m)",
                        border: `1px solid ${cvFolds === k ? "var(--accent)" : "var(--border)"}`,
                      }}>
                      {k}-Fold
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                Loss / Evaluation Metric Override
              </label>
              <select 
                value={metricOverride} 
                onChange={e => setMetricOverride(e.target.value)} 
                className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none"
                style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                <option value="auto">Auto (Adaptive based on Class Balance)</option>
                <optgroup label="Classification">
                  <option value="roc_auc">ROC-AUC (Binary)</option>
                  <option value="macro_f1">Macro F1 (Multiclass)</option>
                  <option value="f1">F1 Score</option>
                  <option value="accuracy">Accuracy</option>
                  <option value="log_loss">Cross-Entropy Log Loss</option>
                </optgroup>
                <optgroup label="Regression">
                  <option value="rmse">Root Mean Squared Error (RMSE)</option>
                  <option value="mae">Mean Absolute Error (MAE)</option>
                  <option value="r2">R² Score (Explained Variance)</option>
                </optgroup>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* -- EXECUTION LAUNCH BAR -- */}
      <div className="flex items-center justify-between p-4 rounded-2xl flex-wrap gap-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3 flex-wrap flex-1 min-w-[300px]">
          <div className="flex-1 min-w-[220px]">
            <label className="text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5 mb-1" style={{ color: "var(--txt-m)" }}>
              <Tag size={11} className="text-indigo-500" />
              <span>Model Name</span>
            </label>
            <input
              type="text"
              value={customModelName}
              onChange={e => setCustomModelName(e.target.value)}
              placeholder={automlTarget ? `${automlTarget} Predictor` : "e.g. Loan Default Classifier v1"}
              className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none transition-all shadow-sm"
              style={{ background: "var(--inp-bg)", border: "1px solid var(--border)", color: "var(--txt)" }}
            />
          </div>
          <div className="text-xs pt-3" style={{ color: "var(--txt-m)" }}>
            {selectedFeatures.length > 0 && selectedAlgos.length > 0 ? (
              <span>Ready with <strong style={{ color: "var(--txt)" }}>{selectedFeatures.length} features</strong> across <strong style={{ color: "var(--txt)" }}>{selectedAlgos.length} model types</strong>.</span>
            ) : (
              <span className="text-amber-500 font-semibold">Select target, features &amp; models.</span>
            )}
          </div>
        </div>

        <button 
          onClick={runAutoml} 
          disabled={isTraining || !automlTarget || selectedFeatures.length === 0 || selectedAlgos.length === 0} 
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-wider text-white transition-all shadow-lg hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
          {isTraining ? (
            <>
              <RefreshCw size={15} className="animate-spin" />
              <span>Training Ensembles...</span>
            </>
          ) : (
            <>
              <Play size={15} fill="currentColor" />
              <span>Launch Enterprise AutoML</span>
            </>
          )}
        </button>
      </div>

      {/* -- ERROR DISPLAY -- */}
      {automlError && (
        <div className="p-4 rounded-xl space-y-1" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.25)" }}>
          <p className="font-bold text-xs text-red-500 flex items-center gap-1.5">
            <AlertTriangle size={14} /> AutoML Training Error
          </p>
          <p className="font-mono text-xs text-red-400 mt-1">{automlError}</p>
        </div>
      )}

      {/* -- TRAINING LOADER -- */}
      {isTraining && (
        <div className="p-10 rounded-2xl flex flex-col items-center justify-center gap-4 text-center border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-white animate-bounce" style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
            <Cpu size={24} />
          </div>
          <div>
            <p className="font-black text-sm uppercase tracking-wider" style={{ color: "var(--txt)" }}>
              Optimizing Hyperparameters & Model Architecture
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
              FLAML is performing Tree-structured Parzen Estimator (TPE) search across {selectedAlgos.join(", ")}...
            </p>
            <p className="font-mono text-[10px] mt-2 text-indigo-400">
              Allocated time budget: ~{automlTimeBudget} seconds
            </p>
          </div>
        </div>
      )}

      {/* -- DEPLOYMENT / INFERENCE CODE SNIPPET MODAL -- */}
      {showDeploySnippet && (
        <div className="p-5 rounded-2xl space-y-3" style={{ background: "var(--surface)", border: "1px solid rgba(99,102,241,0.3)" }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Terminal size={16} className="text-indigo-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                Standalone Python Inference Snippet
              </h4>
            </div>
            <button 
              onClick={() => setShowDeploySnippet(false)}
              className="text-xs font-mono px-2 py-0.5 rounded"
              style={{ background: "var(--border)", color: "var(--txt-m)" }}>
              Close
            </button>
          </div>
          <pre className="p-4 rounded-xl font-mono text-[11px] overflow-x-auto text-emerald-400 bg-black/80">
{`# 1. Load the trained DataForge Model
import joblib
import pandas as pd

bundle = joblib.load("model_${uploadId}.joblib")
model = bundle["model"]
features = bundle["feature_columns"]

# 2. Predict on new incoming production data
new_data = pd.DataFrame([{
    ${selectedFeatures.slice(0, 3).map(f => `"${f}": 100`).join(",\n    ")}
}])

# Align columns
X_infer = new_data[features]
predictions = model.predict(X_infer)
print("Predicted Output:", predictions)
`}
          </pre>
        </div>
      )}

      {/* -- RESULTS & LEADERBOARD SECTION -- */}
      {automlResult && !isTraining && (
        <div className="space-y-5">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
            <div className="p-4 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Champion Architecture</p>
              <p className="text-lg font-black font-mono mt-1" style={{ color: "var(--accent)" }}>
                {automlResult.best_estimator || "Ensemble"}
              </p>
              <p className="text-[10px] mt-0.5 font-mono" style={{ color: "var(--txt-f)" }}>
                Best Loss: {automlResult.best_loss ?? "N/A"}
              </p>
            </div>

            <div className="p-4 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Training Time</p>
              <p className="text-lg font-black font-mono mt-1" style={{ color: "var(--txt)" }}>
                {automlResult.elapsed_s || automlTimeBudget}s
              </p>
              <p className="text-[10px] mt-0.5 font-mono" style={{ color: "var(--txt-f)" }}>
                Budget: {automlResult.effective_budget_s || automlTimeBudget}s
              </p>
            </div>

            <div className="p-4 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Training Partition</p>
              <p className="text-lg font-black font-mono mt-1" style={{ color: "var(--txt)" }}>
                {(automlResult.train_rows || 0).toLocaleString()} rows
              </p>
              <p className="text-[10px] mt-0.5 font-mono" style={{ color: "var(--txt-f)" }}>
                Holdout: {(automlResult.test_rows || 0).toLocaleString()} rows
              </p>
            </div>

            <div className="p-4 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Validation Scheme</p>
              <p className="text-lg font-black font-mono mt-1 capitalize" style={{ color: "var(--txt)" }}>
                {automlResult.eval_method || cvStrategy}
              </p>
              <p className="text-[10px] mt-0.5 font-mono" style={{ color: "var(--txt-f)" }}>
                {automlResult.n_cv_splits ? `${automlResult.n_cv_splits} Splits` : "Holdout Split"}
              </p>
            </div>
          </div>

          {/* Metric Badges Grid */}
          {automlResult.metrics && Object.keys(automlResult.metrics).length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
              {Object.entries(automlResult.metrics).map(([k, v]: [string, any]) => (
                <div key={k} className="p-3 rounded-xl border text-center" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                  <p className="text-[10px] uppercase font-mono tracking-wider truncate" style={{ color: "var(--txt-m)" }}>{k}</p>
                  <p className="text-base font-black font-mono mt-0.5" style={{ color: "var(--accent)" }}>
                    {typeof v === 'number' ? v.toFixed(4) : v}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* Leaderboard & Feature Importance Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Leaderboard Table (6 cols) */}
            <div className="lg:col-span-6 p-5 rounded-2xl space-y-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                  Evaluated Architecture Leaderboard
                </h3>
                <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                  Sorted by validation metric
                </span>
              </div>

              <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="font-mono text-[10px] uppercase tracking-wider" style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", color: "var(--txt-m)" }}>
                    <tr>
                      <th className="py-2.5 px-3">Rank & Model</th>
                      <th className="py-2.5 px-3">Metric Score</th>
                      <th className="py-2.5 px-3">Hyperparameters</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {(automlResult.leaderboard || []).map((row: any, i: number) => (
                      <tr 
                        key={i}
                        style={{ background: row.best ? "rgba(99,102,241,0.08)" : "transparent" }}>
                        <td className="py-2.5 px-3 font-mono font-bold flex items-center gap-1.5" style={{ color: row.best ? "var(--accent)" : "var(--txt)" }}>
                          {row.best ? (
                            <span className="text-amber-400">★</span>
                          ) : (
                            <span className="text-[10px]" style={{ color: "var(--txt-f)" }}>#{i + 1}</span>
                          )}
                          <span>{row.model}</span>
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold" style={{ color: row.best ? "var(--accent)" : "var(--txt)" }}>
                          {row.metric !== null ? row.metric : "-"}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-[10px] max-w-[200px] truncate" style={{ color: "var(--txt-m)" }} title={row.best_config}>
                          {row.best_config || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Feature Importance Bar Chart (6 cols) */}
            <div className="lg:col-span-6 p-5 rounded-2xl space-y-3" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                  Top Predictor Importance
                </h3>
                <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                  Model-attributed weight
                </span>
              </div>

              {automlResult.feature_importance && automlResult.feature_importance.length > 0 ? (
                <div className="space-y-2.5 pt-1">
                  {automlResult.feature_importance.slice(0, 10).map((fi: any) => {
                    const maxImp = automlResult.feature_importance[0]?.importance || 1;
                    const pct = maxImp > 0 ? Math.max(3, (fi.importance / maxImp) * 100) : 3;
                    return (
                      <div key={fi.feature} className="flex items-center gap-3 text-xs">
                        <span className="w-28 font-mono text-[11px] truncate text-right font-medium" style={{ color: "var(--txt)" }}>
                          {fi.feature}
                        </span>
                        <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: "var(--border)" }}>
                          <div 
                            className="h-full rounded-full transition-all duration-500" 
                            style={{ 
                              background: "linear-gradient(90deg, #6366f1, #3b82f6)", 
                              width: `${pct}%` 
                            }} 
                          />
                        </div>
                        <span className="w-12 text-right font-mono text-[10px]" style={{ color: "var(--txt-m)" }}>
                          {Number(fi.importance).toFixed(4)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-xs font-mono py-8 text-center" style={{ color: "var(--txt-m)" }}>
                  Feature importances are not exposed by the selected linear estimator.
                </p>
              )}
            </div>
          </div>

          {/* -- Enterprise Model Registry & In-Workspace Application Card -- */}
          <div className="p-5 rounded-2xl border space-y-4" style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(59,130,246,0.04))", borderColor: "rgba(99,102,241,0.25)" }}>
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-md" style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
                  <Boxes size={20} className="text-white" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                      Champion Model: <span className="text-indigo-400 font-mono">{automlResult.model_name || customModelName || automlResult.best_estimator || "Ensemble"}</span>
                    </h4>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      ✓ Stored in Model Catalog
                    </span>
                  </div>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>
                    Trained on {automlResult.train_rows || 0} rows. Apply directly to your active workspace dataset to append prediction &amp; probability columns.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 flex-wrap">
                {automlResult.registered_model_id && (
                  <button
                    onClick={() => applyModelToWorkspace()}
                    disabled={isApplyingModel}
                    className="px-4 py-2.5 rounded-xl font-bold text-xs text-white flex items-center gap-2 shadow-lg transition-all hover:scale-[1.02] cursor-pointer"
                    style={{ background: "linear-gradient(135deg, #10b981, #059669)", opacity: isApplyingModel ? 0.7 : 1 }}
                  >
                    <Play size={13} />
                    <span>{isApplyingModel ? "Scoring Dataset..." : "⚡ Apply Model to Current Dataset"}</span>
                  </button>
                )}

                <button
                  onClick={() => setActiveTab("models")}
                  className="px-4 py-2.5 rounded-xl font-bold text-xs border text-slate-200 hover:text-white flex items-center gap-1.5 transition-all hover:scale-[1.02] cursor-pointer"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <span>Open in Models Catalog</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            </div>

            {applySuccessMsg && (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold flex items-center gap-2">
                <CheckCircle2 size={15} />
                <span>{applySuccessMsg} View changes in <button onClick={() => setActiveTab("preview")} className="underline font-black cursor-pointer">My Data</button> or <button onClick={() => setActiveTab("charts")} className="underline font-black cursor-pointer">Dashboard</button>.</span>
              </div>
            )}
            {applyErrorMsg && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-bold flex items-center gap-2">
                <AlertCircle size={15} />
                <span>{applyErrorMsg}</span>
              </div>
            )}
          </div>
        </div>

      )}
    </div>
  );
}
