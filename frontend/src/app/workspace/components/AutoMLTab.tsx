"use client";

import React, { useState, useEffect, useMemo } from "react";
import { useWorkspace } from "./WorkspaceProvider";
function getShareToken(uid?: string | null): string {
  if (typeof window === "undefined" || !uid) return "";
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get("share_token") || sessionStorage.getItem("df_share_token_" + uid) || sessionStorage.getItem(`df_share_${uid}`) || "";
  } catch (e) {
    return "";
  }
}

import { apiFetch } from "@/lib/api";
import {
  Bot, ShieldAlert, ShieldCheck, AlertTriangle, Sliders,
  Cpu, Check, Download, Play, RefreshCw, Search, Filter,
  Terminal, Code, Layers, Zap, BarChart3, ChevronRight, CheckCircle2, Boxes, ArrowRight, AlertCircle, Tag, X,
  Trophy, Settings2, Sparkles, SlidersHorizontal
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
  { id: "lgbm", name: "LightGBM", tag: "Ultra Fast", desc: "Gradient boosted trees optimized for speed, low memory, and large datasets.", category: "boosting" },
  { id: "xgboost", name: "XGBoost", tag: "High Accuracy", desc: "Extreme gradient boosting with exact greedy split search.", category: "boosting" },
  { id: "catboost", name: "CatBoost", tag: "Categorical", desc: "Symmetric trees with ordered boosting; exceptional for categorical data.", category: "boosting" },
  { id: "rf", name: "Random Forest", tag: "Bagging", desc: "Averaged forest of decision trees; highly resistant to noise and variance.", category: "tree" },
  { id: "extra_tree", name: "Extra Trees", tag: "Randomized", desc: "Extremely randomized trees with lower variance and high training throughput.", category: "tree" },
  { id: "gradient_boosting", name: "Hist Gradient Boosting", tag: "Boosting", desc: "Histogram-based gradient boosting trees with fast numerical binning.", category: "boosting" },
  { id: "linear", name: "Linear / Ridge", tag: "Interpretable", desc: "L1/L2 regularized linear model providing an interpretable baseline.", category: "linear" },
  { id: "decision_tree", name: "Decision Tree", tag: "Tree", desc: "Single transparent decision tree; fast and easily visualizable.", category: "tree" },
  { id: "knn", name: "K-Nearest Neighbors", tag: "Instance-based", desc: "Non-parametric distance-weighted classification and regression.", category: "neighbors" },
  { id: "svm", name: "Support Vector Machine", tag: "Margin-based", desc: "Maximal-margin hyperplane classifier/regressor with regularized boundary.", category: "svm" },
];

export function AutoMLTab() {
  const { profile, cleanProfile, uploadId, setActiveTab, automlMeta, setAutomlMeta, refreshWorkspace, cleanResult } = useWorkspace();

  const effectiveProfile = useMemo(() => {
    if (cleanProfile?.columns && Array.isArray(cleanProfile.columns) && cleanProfile.columns.length > 0) {
      return cleanProfile;
    }
    if (cleanResult?.clean_profile?.columns && Array.isArray(cleanResult.clean_profile.columns) && cleanResult.clean_profile.columns.length > 0) {
      return cleanResult.clean_profile;
    }
    if (profile?.columns && Array.isArray(profile.columns) && profile.columns.length > 0) {
      return profile;
    }
    return cleanProfile || cleanResult?.clean_profile || profile || {};
  }, [cleanProfile, cleanResult, profile]);

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

  // Mode & Algorithm Whitelist & Hyperparameters
  const [trainingMode, setTrainingMode] = useState<"tournament" | "manual">("tournament");
  const [manualModel, setManualModel] = useState<string>("xgboost");
  const [selectedAlgos, setSelectedAlgos] = useState<string[]>([
    "lgbm", "xgboost", "catboost", "rf", "extra_tree",
    "gradient_boosting", "linear", "decision_tree", "knn", "svm"
  ]);
  const [hyperparams, setHyperparams] = useState<Record<string, any>>({
    n_estimators: 100,
    max_depth: 6,
    learning_rate: 0.1,
    min_samples_split: 2,
    min_samples_leaf: 1,
    subsample: 1.0,
    C: 1.0,
    alpha: 1.0,
    n_neighbors: 5,
    weights: "uniform",
    metric: "minkowski",
    criterion: "gini",
    max_iter: 1000,
  });
  const [cvStrategy, setCvStrategy] = useState("auto");
  const [cvFolds, setCvFolds] = useState(5);
  const [metricOverride, setMetricOverride] = useState("auto");

  // Detection & Execution
  const [detectedTask, setDetectedTask] = useState("");
  const [detectedNUnique, setDetectedNUnique] = useState(0);
  const [isTraining, setIsTraining] = useState(false);
  const [automlError, setAutomlError] = useState("");

  // Auto-dismiss error notifications after 6 seconds
  useEffect(() => {
    if (!automlError) return;
    const timer = setTimeout(() => setAutomlError(""), 6000);
    return () => clearTimeout(timer);
  }, [automlError]);
  const [automlResult, setAutomlResult] = useState<any>(null);
  // Restore previous AutoML result on refresh
  useEffect(() => {
    if (automlMeta && !automlResult) {
      setAutomlResult(automlMeta);
      const restoredTarget = automlMeta.target_col || automlMeta.target || "";
      if (restoredTarget) setAutomlTarget(restoredTarget);
      if (automlMeta.task) setDetectedTask(automlMeta.task);
      if (automlMeta.model_name) setCustomModelName(automlMeta.model_name);
      if (Array.isArray(automlMeta.algorithm_whitelist) && automlMeta.algorithm_whitelist.length > 0) {
        const algos = automlMeta.algorithm_whitelist.filter((a: string) => a !== "all");
        if (algos.length > 0) setSelectedAlgos(algos);
      }
    }
  }, [automlMeta]);

  // Available columns from profile (with robust fallback)
  const allColumns: string[] = useMemo(() => {
    const cols = effectiveProfile?.columns || profile?.columns || cleanResult?.clean_profile?.columns || cleanProfile?.columns;
    if (Array.isArray(cols) && cols.length > 0) {
      return cols
        .map((c: any) => (typeof c === "string" ? c : c?.name || c?.col || c?.column || ""))
        .filter(Boolean);
    }
    if (Array.isArray(effectiveProfile?.headers) && effectiveProfile.headers.length > 0) {
      return effectiveProfile.headers.filter(Boolean);
    }
    return [];
  }, [effectiveProfile, profile, cleanResult, cleanProfile]);

  // Fast map of column metadata from profile
  const profileColMap = useMemo(() => {
    const map: Record<string, any> = {};
    const cols = effectiveProfile?.columns || profile?.columns || cleanResult?.clean_profile?.columns || [];
    if (Array.isArray(cols)) {
      cols.forEach((c: any) => {
        const name = typeof c === "string" ? c : c?.name || c?.col || c?.column;
        if (name) map[name] = c;
      });
    }
    return map;
  }, [effectiveProfile, profile, cleanResult]);

  // Auto-suggest a target if none selected yet and columns are available
  const isTargetInitialized = React.useRef(false);
  useEffect(() => {
    if (allColumns.length === 0) return;

    if (!isTargetInitialized.current) {
      isTargetInitialized.current = true;
      if (!automlTarget) {
        const candidate = allColumns.find(c => {
          const lower = c.toLowerCase().trim();
          return ["target", "label", "class", "churn", "status", "outcome", "survived", "y", "is_churn", "fraud", "loan_status"].includes(lower);
        });
        const targetToSet = candidate || allColumns[allColumns.length - 1];
        if (targetToSet) {
          setAutomlTarget(targetToSet);
          setCustomModelName(`${targetToSet.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())} Predictor`);
        }
      }
    } else if (automlTarget && !allColumns.includes(automlTarget)) {
      const candidate = allColumns.find(c => {
        const lower = c.toLowerCase().trim();
        return ["target", "label", "class", "churn", "status", "outcome", "survived", "y", "is_churn", "fraud", "loan_status"].includes(lower);
      });
      const targetToSet = candidate || allColumns[allColumns.length - 1];
      if (targetToSet) {
        setAutomlTarget(targetToSet);
        setCustomModelName(`${targetToSet.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())} Predictor`);
      }
    }
  }, [allColumns, automlTarget]);

  // Active features list: uses deep analysis if available, otherwise immediate local baseline from dataset profile
  const activeFeaturesList: FeatureInfo[] = useMemo(() => {
    if (featuresList && featuresList.length > 0) {
      return featuresList;
    }
    if (allColumns.length === 0) return [];

    return allColumns
      .filter(col => !automlTarget || col !== automlTarget)
      .map(col => {
        const colMeta = profileColMap[col];
        const isObj = typeof colMeta === "object" && colMeta !== null;
        const dtype = isObj ? (colMeta.dtype || colMeta.type || "string") : "string";
        const missingPct = isObj ? (colMeta.null_pct ?? 0) : 0;
        const nUnique = isObj ? (colMeta.n_unique ?? colMeta.unique_count ?? 0) : 0;
        const lower = col.toLowerCase();
        const isId = lower.endsWith("_id") || lower === "id" || lower.endsWith("id") || lower.endsWith("_uuid");

        return {
          name: col,
          dtype: dtype,
          missing_count: isObj && colMeta.null_count ? colMeta.null_count : 0,
          missing_pct: missingPct,
          n_unique: nUnique,
          is_id: isId,
          correlation: null,
          leakage_risk: "low" as const,
          recommendation: isId ? "drop_id" as const : missingPct >= 60 ? "drop_missing" as const : "include" as const,
        };
      });
  }, [featuresList, allColumns, automlTarget, profileColMap]);

  // Keep selected features in sync if empty
  useEffect(() => {
    if (selectedFeatures.length === 0 && activeFeaturesList.length > 0) {
      const safe = activeFeaturesList
        .filter(f => f.name !== automlTarget && f.recommendation === "include" && !f.is_id)
        .map(f => f.name);
      setSelectedFeatures(safe.length > 0 ? safe : activeFeaturesList.filter(f => f.name !== automlTarget).map(f => f.name));
    }
  }, [activeFeaturesList, selectedFeatures.length, automlTarget]);

  // When target changes, analyze task & feature signals
  useEffect(() => {
    if (automlTarget) {
      setSelectedFeatures(prev => prev.filter(c => c !== automlTarget));
      runFeatureAnalysis(automlTarget);
    } else {
      setFeaturesList([]);
      setDetectedTask("");
      setDetectedNUnique(0);
    }
  }, [automlTarget, uploadId]);

  const runFeatureAnalysis = async (target: string) => {
    if (!target) return;

    // Fast local heuristic for task while backend analyzes
    const targetMeta = profileColMap[target];
    if (targetMeta && typeof targetMeta === "object") {
      const dt = (targetMeta.dtype || targetMeta.type || "").toLowerCase();
      const nUniq = targetMeta.n_unique ?? targetMeta.unique_count ?? 0;
      if (dt.includes("object") || dt.includes("str") || dt.includes("cat") || dt.includes("bool") || (nUniq > 0 && nUniq <= 10)) {
        setDetectedTask(nUniq === 2 ? "binary classification" : "multiclass classification");
        if (nUniq > 0) setDetectedNUnique(nUniq);
      } else if (dt.includes("int") || dt.includes("float")) {
        setDetectedTask("regression");
        if (nUniq > 0) setDetectedNUnique(nUniq);
      }
    }

    if (!uploadId) return;
    setIsAnalyzingFeatures(true);
    try {
      const shareToken = getShareToken(uploadId);
      // 1. Detect task
      const taskRes = await apiFetch(`/automl/detect-task?upload_id=${encodeURIComponent(uploadId || '')}${shareToken ? `&share_token=${encodeURIComponent(shareToken)}` : ""}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_col: target, upload_id: uploadId, share_token: shareToken }),
      });
      if (taskRes.ok) {
        const taskData = await taskRes.json();
        if (taskData.task) setDetectedTask(taskData.task);
        if (taskData.n_unique !== undefined) setDetectedNUnique(taskData.n_unique);
      }

      // 2. Comprehensive Feature Analysis & Leakage Audit
      const featRes = await apiFetch(`/automl/feature-analysis?upload_id=${encodeURIComponent(uploadId || '')}${shareToken ? `&share_token=${encodeURIComponent(shareToken)}` : ""}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_col: target, upload_id: uploadId, share_token: shareToken }),
      });

      if (featRes.ok) {
        const featData = await featRes.json();
        if (featData.features && Array.isArray(featData.features)) {
          setFeaturesList(featData.features);
          // Auto-select features recommended as "include" (omit high leakage, ID columns, and target)
          const recommended = featData.features
            .filter((f: FeatureInfo) => f.recommendation === "include" && f.name !== target)
            .map((f: FeatureInfo) => f.name);
          setSelectedFeatures(recommended.length > 0 ? recommended : featData.features.filter((f: FeatureInfo) => f.name !== target).map((f: FeatureInfo) => f.name));
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
    if (colName === automlTarget) return;
    setSelectedFeatures(prev =>
      prev.includes(colName) ? prev.filter(c => c !== colName) : [...prev, colName]
    );
  };

  // Batch feature selection helpers
  const selectAllFeatures = () => {
    setSelectedFeatures(activeFeaturesList.filter(f => f.name !== automlTarget).map(f => f.name));
  };

  const selectSafeFeaturesOnly = () => {
    const safe = activeFeaturesList
      .filter(f => f.name !== automlTarget && f.leakage_risk !== "high" && !f.is_id)
      .map(f => f.name);
    setSelectedFeatures(safe.length > 0 ? safe : activeFeaturesList.filter(f => f.name !== automlTarget).map(f => f.name));
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
    const sourceList = activeFeaturesList.length > 0 ? activeFeaturesList : (
      allColumns.map(col => {
        const colMeta = profileColMap[col];
        const isObj = typeof colMeta === "object" && colMeta !== null;
        const dtype = isObj ? (colMeta.dtype || colMeta.type || "string") : "string";
        const missingPct = isObj ? (colMeta.null_pct ?? 0) : 0;
        const nUnique = isObj ? (colMeta.n_unique ?? colMeta.unique_count ?? 0) : 0;
        const lower = col.toLowerCase();
        const isId = lower.endsWith("_id") || lower === "id";
        return {
          name: col,
          dtype: dtype,
          missing_count: 0,
          missing_pct: missingPct,
          n_unique: nUnique,
          is_id: isId,
          correlation: null,
          leakage_risk: "low" as const,
          recommendation: isId ? "drop_id" as const : "include" as const,
        };
      })
    );

    return sourceList.filter(f => {
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
  }, [activeFeaturesList, allColumns, profileColMap, featureSearch, featureFilter]);

  const highRiskCount = useMemo(() => {
    return activeFeaturesList.filter(f => f.leakage_risk === "high").length;
  }, [activeFeaturesList]);

  // Execute Training
  const runAutoml = async () => {
    if (!automlTarget || !uploadId) return;
    if (selectedFeatures.length === 0) {
      setAutomlError("You must select at least one feature column for training.");
      return;
    }
    if (trainingMode === "tournament" && selectedAlgos.length === 0) {
      setAutomlError("You must select at least one algorithm from the whitelist for tournament mode.");
      return;
    }

    setIsTraining(true);
    setAutomlError("");
    setAutomlResult(null);

    try {
      const shareToken = getShareToken(uploadId);
      const trainUrl = `/automl/train?upload_id=${encodeURIComponent(uploadId || '')}${shareToken ? `&share_token=${encodeURIComponent(shareToken)}` : ""}`;
      const res = await apiFetch(trainUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_col: automlTarget,
          task_choice: automlTask,
          time_budget: parseInt(automlTimeBudget, 10),
          test_size: parseFloat(automlTestSize),
          feature_whitelist: selectedFeatures,
          algorithm_whitelist: trainingMode === "tournament" ? selectedAlgos : [manualModel],
          cv_strategy: cvStrategy,
          cv_folds: cvFolds,
          metric_override: metricOverride,
          upload_id: uploadId,
          share_token: shareToken,
          model_name: customModelName.trim() || undefined,
          mode: trainingMode,
          selected_model: trainingMode === "manual" ? manualModel : undefined,
          hyperparameters: trainingMode === "manual" ? hyperparams : undefined,
        }),
      });

      if (!res.ok) {
        let errStr = "AutoML training initiation failed.";
        try {
          const data = await res.json();
          if (data.detail) errStr = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
          else if (data.error) errStr = data.error;
        } catch (e) { }
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
              const shareToken = getShareToken(uploadId);
              const metaRes = await apiFetch(`/workspace/state?upload_id=${encodeURIComponent(uploadId || '')}${shareToken ? `&share_token=${encodeURIComponent(shareToken)}` : ""}`);
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
      if (refreshWorkspace && uploadId) {
        refreshWorkspace(uploadId);
      }
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

        </div>

        <div className="flex items-center gap-2.5">
          {automlResult && (
            <>
              <button
                onClick={() => setActiveTab("models")}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer"
                style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1", border: "1px solid rgba(99,102,241,0.25)" }}>
                <Boxes size={14} />
                <span>Models Catalog</span>
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
      <div className="p-5 rounded-2xl space-y-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        {allColumns.length === 0 ? (
          <div className="py-8 px-4 text-center space-y-3">
            <div className="inline-flex p-3 rounded-2xl mb-1 text-white shadow-md" style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
              <Sliders size={22} />
            </div>
            <h4 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
              No Dataset Attributes Available
            </h4>
            <p className="text-xs max-w-md mx-auto" style={{ color: "var(--txt-m)" }}>
              Please upload or select a dataset in the workspace to inspect attributes, audit correlations, and train AutoML models.
            </p>
            <button
              type="button"
              onClick={() => setActiveTab("preview")}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white shadow-sm hover:opacity-90 transition-all cursor-pointer"
              style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
              Go to Data Preview / Ingestion
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Sliders size={16} style={{ color: "var(--accent)" }} />
                  <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                    Dataset Attributes &amp; Predictor Whitelist
                  </h3>
                  <span className="text-xs px-2 py-0.5 rounded-full font-mono font-bold" style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1" }}>
                    {selectedFeatures.length} of {activeFeaturesList.length} Predictors Selected
                  </span>
                  {automlTarget ? (
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold" style={{ background: "rgba(99,102,241,0.15)", color: "#6366f1" }}>
                      Target: {automlTarget} (Y)
                    </span>
                  ) : (
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-bold" style={{ background: "rgba(245,158,11,0.15)", color: "#f59e0b" }}>
                      Target not selected
                    </span>
                  )}
                  {isAnalyzingFeatures && (
                    <span className="inline-flex items-center gap-1.5 text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-500 animate-pulse">
                      <RefreshCw size={11} className="animate-spin" />
                      <span>Auditing signal correlations...</span>
                    </span>
                  )}
                </div>
                <p className="text-xs mt-0.5" style={{ color: "var(--txt-m)" }}>
                  Audit column data types, inspect missingness, eliminate target leakage, and whitelist predictor attributes for AutoML training.
                </p>
              </div>

              {/* Batch Selection Action Buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  type="button"
                  onClick={selectSafeFeaturesOnly}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all cursor-pointer"
                  style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", border: "1px solid rgba(16,185,129,0.25)" }}>
                  <ShieldCheck size={12} />
                  <span>Select Safe Only</span>
                </button>
                <button
                  type="button"
                  onClick={selectAllFeatures}
                  className="px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all cursor-pointer"
                  style={{ background: "var(--border)", color: "var(--txt)" }}>
                  Select All
                </button>
                <button
                  type="button"
                  onClick={deselectAllFeatures}
                  className="px-2.5 py-1 rounded-lg text-[11px] font-bold transition-all cursor-pointer"
                  style={{ background: "var(--border)", color: "var(--txt)" }}>
                  Clear
                </button>
              </div>
            </div>

            {/* Informational Prompt when no target selected yet */}
            {!automlTarget && (
              <div className="p-3.5 rounded-xl flex items-center justify-between gap-3" style={{ background: "rgba(99,102,241,0.08)", border: "1px solid rgba(99,102,241,0.25)" }}>
                <div className="flex items-center gap-2.5">
                  <AlertCircle size={16} className="text-indigo-500 shrink-0" />
                  <p className="text-xs font-medium" style={{ color: "var(--txt)" }}>
                    Choose a <strong>Target Variable (Y)</strong> to predict. You can select one from the dropdown above or click <strong>&quot;Set as Target&quot;</strong> on any attribute row below.
                  </p>
                </div>
              </div>
            )}

            {/* High Risk Leakage Banner */}
            {highRiskCount > 0 && automlTarget && (
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
                  placeholder="Search attribute names..."
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
                    type="button"
                    onClick={() => setFeatureFilter(tab)}
                    className={`px-2.5 py-1.5 rounded-lg text-[10px] font-bold capitalize transition-all cursor-pointer ${featureFilter === tab ? 'text-white' : ''}`}
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

            {/* Attributes & Features Table */}
            {displayedFeatures.length === 0 ? (
              <div className="p-8 text-center space-y-2 border rounded-xl" style={{ borderColor: "var(--border)" }}>
                <p className="text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
                  No attributes match your filter criteria.
                </p>
                {(featureSearch || featureFilter !== "all") && (
                  <button
                    type="button"
                    onClick={() => { setFeatureSearch(""); setFeatureFilter("all"); }}
                    className="text-[11px] font-bold text-indigo-500 hover:underline cursor-pointer">
                    Reset Search &amp; Filters
                  </button>
                )}
              </div>
            ) : (
              <div className="max-h-[340px] overflow-y-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="sticky top-0 z-10 font-mono text-[10px] uppercase tracking-wider" style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", color: "var(--txt-m)" }}>
                    <tr>
                      <th className="py-2.5 px-3 w-10 text-center">Inc.</th>
                      <th className="py-2.5 px-3">Attribute Name</th>
                      <th className="py-2.5 px-3">Role / Action</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3">Null %</th>
                      <th className="py-2.5 px-3">Unique</th>
                      <th className="py-2.5 px-3">Signal (Corr)</th>
                      <th className="py-2.5 px-3">Leakage Risk</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {displayedFeatures.map(f => {
                      const isTarget = automlTarget === f.name;
                      const isSelected = selectedFeatures.includes(f.name);
                      return (
                        <tr
                          key={f.name}
                          onClick={() => {
                            if (!isTarget) toggleFeature(f.name);
                          }}
                          className={`transition-colors ${isTarget ? 'bg-indigo-500/5 dark:bg-indigo-500/10' : 'cursor-pointer hover:bg-black/5 dark:hover:bg-white/5'}`}
                          style={{ background: isTarget ? "rgba(99,102,241,0.06)" : isSelected ? "rgba(99,102,241,0.02)" : "transparent" }}>
                          <td className="py-2 px-3 text-center" onClick={e => e.stopPropagation()}>
                            {isTarget ? (
                              <span className="inline-flex items-center justify-center w-4 h-4 rounded text-indigo-500 bg-indigo-500/15" title="Target variable">
                                <Zap size={11} />
                              </span>
                            ) : (
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleFeature(f.name)}
                                className="rounded accent-[var(--accent)] cursor-pointer"
                              />
                            )}
                          </td>
                          <td className="py-2 px-3 font-semibold font-mono text-[11px]" style={{ color: isTarget ? "var(--accent)" : isSelected ? "var(--txt)" : "var(--txt-m)" }}>
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span>{f.name}</span>
                              {isTarget && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold bg-indigo-500 text-white">
                                  TARGET (Y)
                                </span>
                              )}
                              {f.is_id && (
                                <span className="text-[9px] px-1 py-0.5 rounded font-sans font-bold bg-amber-500/10 text-amber-500">
                                  ID Candidate
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="py-2 px-3" onClick={e => e.stopPropagation()}>
                            {isTarget ? (
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-500">
                                Target Variable
                              </span>
                            ) : (
                              <button
                                type="button"
                                onClick={() => {
                                  setAutomlTarget(f.name);
                                  setCustomModelName(`${f.name.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())} Predictor`);
                                }}
                                className="text-[10px] font-bold px-2 py-0.5 rounded-lg border transition-all hover:bg-indigo-500/10 hover:border-indigo-500 text-indigo-500 cursor-pointer"
                                style={{ borderColor: "var(--border)" }}>
                                Set as Target
                              </button>
                            )}
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
                            {isTarget ? (
                              <span className="font-mono text-[10px] text-indigo-500 font-bold">1.000 (Target)</span>
                            ) : f.correlation !== null ? (
                              <span style={{ color: Math.abs(f.correlation) >= 0.9 ? "#ef4444" : Math.abs(f.correlation) >= 0.4 ? "#10b981" : "var(--txt-m)" }}>
                                {f.correlation > 0 ? `+${f.correlation.toFixed(3)}` : f.correlation.toFixed(3)}
                              </span>
                            ) : (
                              <span style={{ color: "var(--txt-f)" }}>-</span>
                            )}
                          </td>
                          <td className="py-2 px-3">
                            {isTarget ? (
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-500">
                                <Zap size={10} /> Target
                              </span>
                            ) : f.leakage_risk === "high" ? (
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
          </>
        )}
      </div>

      {/* -- SECTION 3: MODE SELECTOR & ALGORITHMS / HYPERPARAMETERS -- */}
      <div className="p-5 rounded-2xl space-y-5" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        {/* Mode Segmented Controls */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4" style={{ borderColor: "var(--border)" }}>
          <div>
            <div className="flex items-center gap-2">
              <Sparkles size={16} style={{ color: "var(--accent)" }} />
              <h3 className="text-sm font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                Model Selection &amp; Tuning Mode
              </h3>
            </div>
            <p className="text-xs mt-0.5" style={{ color: "var(--txt-m)" }}>
              Choose between automated multi-model tournament ranking or manual fine-tuning.
            </p>
          </div>

          <div className="flex items-center p-1 rounded-xl" style={{ background: "var(--inp-bg)", border: "1px solid var(--border)" }}>
            <button
              type="button"
              onClick={() => setTrainingMode("tournament")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${trainingMode === "tournament" ? "shadow-sm text-white" : ""}`}
              style={{
                background: trainingMode === "tournament" ? "linear-gradient(135deg, #6366f1, #3b82f6)" : "transparent",
                color: trainingMode === "tournament" ? "#ffffff" : "var(--txt-m)",
              }}>
              <Trophy size={13} />
              <span>Leaderboard Tournament</span>
            </button>
            <button
              type="button"
              onClick={() => setTrainingMode("manual")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${trainingMode === "manual" ? "shadow-sm text-white" : ""}`}
              style={{
                background: trainingMode === "manual" ? "linear-gradient(135deg, #6366f1, #3b82f6)" : "transparent",
                color: trainingMode === "manual" ? "#ffffff" : "var(--txt-m)",
              }}>
              <Settings2 size={13} />
              <span>Manual Hyperparameter Tuning</span>
            </button>
          </div>
        </div>

        {trainingMode === "tournament" ? (
          /* TOURNAMENT MODE */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* 10 Models Whitelist Grid (7 cols) */}
            <div className="lg:col-span-7 space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <Cpu size={15} style={{ color: "var(--accent)" }} />
                  <span className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                    Tournament Competitors ({selectedAlgos.length}/10 Active)
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedAlgos(AVAILABLE_ALGORITHMS.map(a => a.id))}
                    className="text-[10px] font-bold px-2 py-0.5 rounded border transition-colors hover:border-indigo-400"
                    style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={() => setSelectedAlgos(["lgbm", "xgboost", "catboost", "rf", "extra_tree"])}
                    className="text-[10px] font-bold px-2 py-0.5 rounded border transition-colors hover:border-indigo-400"
                    style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
                    Reset Defaults
                  </button>
                </div>
              </div>
              <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                Selected models will be benchmarked side-by-side on identical train/validation splits, ranked on the live leaderboard, and the champion model will be registered.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                {AVAILABLE_ALGORITHMS.map(algo => {
                  const isChecked = selectedAlgos.includes(algo.id);
                  return (
                    <div
                      key={algo.id}
                      onClick={() => toggleAlgorithm(algo.id)}
                      className="p-3 rounded-xl border cursor-pointer transition-all flex items-start gap-2.5 select-none hover:border-indigo-400/40"
                      style={{
                        background: isChecked ? "rgba(99,102,241,0.06)" : "transparent",
                        borderColor: isChecked ? "rgba(99,102,241,0.4)" : "var(--border)",
                      }}>
                      <div
                        className="w-4 h-4 rounded mt-0.5 flex items-center justify-center transition-all shrink-0"
                        style={{
                          background: isChecked ? "var(--accent)" : "transparent",
                          border: `1.5px solid ${isChecked ? "var(--accent)" : "var(--txt-m)"}`,
                        }}>
                        {isChecked && <Check size={11} className="text-white" strokeWidth={3} />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1.5">
                          <span className="font-bold text-xs truncate" style={{ color: isChecked ? "var(--txt)" : "var(--txt-m)" }}>
                            {algo.name}
                          </span>
                          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded border whitespace-nowrap shrink-0" style={{ background: "var(--inp-bg)", borderColor: "var(--border)", color: "var(--txt-m)" }}>
                            {algo.tag}
                          </span>
                        </div>
                        <p className="text-[10px] mt-0.5 leading-tight line-clamp-2" style={{ color: "var(--txt-f)" }}>
                          {algo.desc}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Validation Strategy & Objective (5 cols) */}
            <div className="lg:col-span-5 space-y-4 lg:border-l lg:pl-5" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2">
                <Layers size={15} style={{ color: "var(--accent)" }} />
                <span className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                  Validation &amp; Objective Tuning
                </span>
              </div>
              <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
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
        ) : (
          /* MANUAL HYPERPARAMETER TUNING MODE */
          <div className="space-y-5">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                  Step 1: Select Model Architecture (1 of 10)
                </span>
                <span className="text-[11px] font-mono text-indigo-400 font-bold">
                  Active: {AVAILABLE_ALGORITHMS.find(a => a.id === manualModel)?.name}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
                {AVAILABLE_ALGORITHMS.map(algo => {
                  const isSelected = manualModel === algo.id;
                  return (
                    <button
                      key={algo.id}
                      type="button"
                      onClick={() => setManualModel(algo.id)}
                      className="p-3 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between"
                      style={{
                        background: isSelected ? "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(59,130,246,0.08))" : "var(--inp-bg)",
                        borderColor: isSelected ? "var(--accent)" : "var(--border)",
                        boxShadow: isSelected ? "0 0 0 1px var(--accent)" : "none",
                      }}>
                      <div>
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-black text-xs" style={{ color: isSelected ? "var(--accent)" : "var(--txt)" }}>
                            {algo.name}
                          </span>
                          <span className="text-[9px] font-mono px-1 py-0.5 rounded border" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
                            {algo.tag}
                          </span>
                        </div>
                        <p className="text-[10px] mt-1 line-clamp-2 leading-tight" style={{ color: "var(--txt-f)" }}>
                          {algo.desc}
                        </p>
                      </div>
                      {isSelected && (
                        <div className="mt-2 text-[10px] font-bold text-indigo-400 flex items-center gap-1">
                          <CheckCircle2 size={11} /> Selected for Custom Tuning
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Hyperparameter Controls based on selected model */}
            <div className="p-4 rounded-xl border space-y-4" style={{ background: "var(--inp-bg)", borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between flex-wrap gap-2 border-b pb-2.5" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center gap-2">
                  <SlidersHorizontal size={15} className="text-indigo-500" />
                  <span className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                    Step 2: Customize {AVAILABLE_ALGORITHMS.find(a => a.id === manualModel)?.name} Hyperparameters
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setHyperparams({
                    n_estimators: 100,
                    max_depth: 6,
                    learning_rate: 0.1,
                    min_samples_split: 2,
                    min_samples_leaf: 1,
                    subsample: 1.0,
                    C: 1.0,
                    alpha: 1.0,
                    n_neighbors: 5,
                    weights: "uniform",
                    metric: "minkowski",
                    criterion: "gini",
                    max_iter: 1000,
                  })}
                  className="text-[10px] font-bold text-indigo-400 hover:underline">
                  Reset to Recommended
                </button>
              </div>

              {/* Dynamic Form Controls */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* 1. Tree / Boosting Models */}
                {["lgbm", "xgboost", "catboost", "rf", "extra_tree", "gradient_boosting"].includes(manualModel) && (
                  <>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Number of Estimators (Trees)
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="10"
                          max="400"
                          step="10"
                          value={hyperparams.n_estimators || 100}
                          onChange={e => setHyperparams(prev => ({ ...prev, n_estimators: parseInt(e.target.value, 10) }))}
                          className="flex-1 accent-[var(--accent)]"
                        />
                        <span className="font-mono text-xs font-bold w-12 text-right" style={{ color: "var(--txt)" }}>
                          {hyperparams.n_estimators || 100}
                        </span>
                      </div>
                      <span className="text-[10px] mt-0.5 block" style={{ color: "var(--txt-f)" }}>Default: 100 trees</span>
                    </div>

                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Max Tree Depth
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="1"
                          max="16"
                          step="1"
                          value={hyperparams.max_depth || 6}
                          onChange={e => setHyperparams(prev => ({ ...prev, max_depth: parseInt(e.target.value, 10) }))}
                          className="flex-1 accent-[var(--accent)]"
                        />
                        <span className="font-mono text-xs font-bold w-12 text-right" style={{ color: "var(--txt)" }}>
                          {hyperparams.max_depth || 6}
                        </span>
                      </div>
                      <span className="text-[10px] mt-0.5 block" style={{ color: "var(--txt-f)" }}>Controls model complexity</span>
                    </div>

                    {["lgbm", "xgboost", "catboost", "gradient_boosting"].includes(manualModel) && (
                      <div>
                        <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                          Learning Rate (η)
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min="0.01"
                            max="0.4"
                            step="0.01"
                            value={hyperparams.learning_rate || 0.1}
                            onChange={e => setHyperparams(prev => ({ ...prev, learning_rate: parseFloat(e.target.value) }))}
                            className="flex-1 accent-[var(--accent)]"
                          />
                          <span className="font-mono text-xs font-bold w-12 text-right" style={{ color: "var(--txt)" }}>
                            {hyperparams.learning_rate || 0.1}
                          </span>
                        </div>
                        <span className="text-[10px] mt-0.5 block" style={{ color: "var(--txt-f)" }}>Step size shrinkage</span>
                      </div>
                    )}

                    {["lgbm", "xgboost"].includes(manualModel) && (
                      <div>
                        <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                          Subsample Ratio
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min="0.5"
                            max="1.0"
                            step="0.05"
                            value={hyperparams.subsample || 1.0}
                            onChange={e => setHyperparams(prev => ({ ...prev, subsample: parseFloat(e.target.value) }))}
                            className="flex-1 accent-[var(--accent)]"
                          />
                          <span className="font-mono text-xs font-bold w-12 text-right" style={{ color: "var(--txt)" }}>
                            {hyperparams.subsample || 1.0}
                          </span>
                        </div>
                        <span className="text-[10px] mt-0.5 block" style={{ color: "var(--txt-f)" }}>Stochastic row subsampling</span>
                      </div>
                    )}

                    {["rf", "extra_tree"].includes(manualModel) && (
                      <div>
                        <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                          Min Samples Split
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            min="2"
                            max="20"
                            step="1"
                            value={hyperparams.min_samples_split || 2}
                            onChange={e => setHyperparams(prev => ({ ...prev, min_samples_split: parseInt(e.target.value, 10) }))}
                            className="flex-1 accent-[var(--accent)]"
                          />
                          <span className="font-mono text-xs font-bold w-12 text-right" style={{ color: "var(--txt)" }}>
                            {hyperparams.min_samples_split || 2}
                          </span>
                        </div>
                        <span className="text-[10px] mt-0.5 block" style={{ color: "var(--txt-f)" }}>Prevents small leaf splits</span>
                      </div>
                    )}
                  </>
                )}

                {/* 2. Decision Tree */}
                {manualModel === "decision_tree" && (
                  <>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Max Depth
                      </label>
                      <input
                        type="range"
                        min="1"
                        max="20"
                        step="1"
                        value={hyperparams.max_depth || 6}
                        onChange={e => setHyperparams(prev => ({ ...prev, max_depth: parseInt(e.target.value, 10) }))}
                        className="w-full accent-[var(--accent)]"
                      />
                      <span className="text-xs font-mono font-bold">{hyperparams.max_depth || 6}</span>
                    </div>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Min Samples Split
                      </label>
                      <input
                        type="range"
                        min="2"
                        max="20"
                        step="1"
                        value={hyperparams.min_samples_split || 2}
                        onChange={e => setHyperparams(prev => ({ ...prev, min_samples_split: parseInt(e.target.value, 10) }))}
                        className="w-full accent-[var(--accent)]"
                      />
                      <span className="text-xs font-mono font-bold">{hyperparams.min_samples_split || 2}</span>
                    </div>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Criterion
                      </label>
                      <select
                        value={hyperparams.criterion || "gini"}
                        onChange={e => setHyperparams(prev => ({ ...prev, criterion: e.target.value }))}
                        className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none"
                        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                        <option value="gini">Gini Impurity (Standard)</option>
                        <option value="entropy">Information Gain (Entropy)</option>
                        <option value="squared_error">Squared Error (Regression)</option>
                      </select>
                    </div>
                  </>
                )}

                {/* 3. Linear / Ridge */}
                {manualModel === "linear" && (
                  <>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Regularization Strength (C / α)
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="0.05"
                          max="10.0"
                          step="0.05"
                          value={hyperparams.C || 1.0}
                          onChange={e => setHyperparams(prev => ({ ...prev, C: parseFloat(e.target.value), alpha: parseFloat(e.target.value) }))}
                          className="flex-1 accent-[var(--accent)]"
                        />
                        <span className="font-mono text-xs font-bold w-12 text-right">{hyperparams.C || 1.0}</span>
                      </div>
                      <span className="text-[10px] mt-0.5 block" style={{ color: "var(--txt-f)" }}>Smaller = stronger regularization</span>
                    </div>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Max Iterations
                      </label>
                      <input
                        type="number"
                        min="100"
                        max="3000"
                        step="100"
                        value={hyperparams.max_iter || 1000}
                        onChange={e => setHyperparams(prev => ({ ...prev, max_iter: parseInt(e.target.value, 10) }))}
                        className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none"
                        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)" }}
                      />
                    </div>
                  </>
                )}

                {/* 4. KNN */}
                {manualModel === "knn" && (
                  <>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Number of Neighbors (K)
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="1"
                          max="25"
                          step="1"
                          value={hyperparams.n_neighbors || 5}
                          onChange={e => setHyperparams(prev => ({ ...prev, n_neighbors: parseInt(e.target.value, 10) }))}
                          className="flex-1 accent-[var(--accent)]"
                        />
                        <span className="font-mono text-xs font-bold w-12 text-right">{hyperparams.n_neighbors || 5}</span>
                      </div>
                    </div>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Weights
                      </label>
                      <select
                        value={hyperparams.weights || "uniform"}
                        onChange={e => setHyperparams(prev => ({ ...prev, weights: e.target.value }))}
                        className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none"
                        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                        <option value="uniform">Uniform (Equal Weight)</option>
                        <option value="distance">Distance Weighted (Closer = Stronger)</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Distance Metric
                      </label>
                      <select
                        value={hyperparams.metric || "minkowski"}
                        onChange={e => setHyperparams(prev => ({ ...prev, metric: e.target.value }))}
                        className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none"
                        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)" }}>
                        <option value="minkowski">Minkowski (Standard)</option>
                        <option value="euclidean">Euclidean (L2 Distance)</option>
                        <option value="manhattan">Manhattan (L1 City Block)</option>
                      </select>
                    </div>
                  </>
                )}

                {/* 5. SVM */}
                {manualModel === "svm" && (
                  <>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Regularization Parameter (C)
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="range"
                          min="0.1"
                          max="10.0"
                          step="0.1"
                          value={hyperparams.C || 1.0}
                          onChange={e => setHyperparams(prev => ({ ...prev, C: parseFloat(e.target.value) }))}
                          className="flex-1 accent-[var(--accent)]"
                        />
                        <span className="font-mono text-xs font-bold w-12 text-right">{hyperparams.C || 1.0}</span>
                      </div>
                    </div>
                    <div>
                      <label className="text-[11px] font-bold uppercase tracking-wider block mb-1" style={{ color: "var(--txt-m)" }}>
                        Max Iterations
                      </label>
                      <input
                        type="number"
                        min="500"
                        max="5000"
                        step="250"
                        value={hyperparams.max_iter || 2000}
                        onChange={e => setHyperparams(prev => ({ ...prev, max_iter: parseInt(e.target.value, 10) }))}
                        className="w-full text-xs font-semibold px-3 py-2 rounded-xl outline-none"
                        style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)" }}
                      />
                    </div>
                  </>
                )}
              </div>

              {/* JSON preview */}
              <div className="pt-2 border-t flex items-center justify-between flex-wrap gap-2 text-[10px] font-mono" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
                <span>Parameters payload:</span>
                <span className="px-2 py-0.5 rounded border" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                  {JSON.stringify(hyperparams)}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* -- EXECUTION LAUNCH BAR -- */}
      <div className="flex items-center justify-between p-4 rounded-2xl flex-wrap gap-4" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
        <div className="flex items-center gap-3 flex-wrap flex-1 min-w-[300px]">
          <div className="text-xs" style={{ color: "var(--txt-m)" }}>
            {!automlTarget ? (
              <span className="text-amber-500 font-semibold flex items-center gap-1.5">
                <AlertTriangle size={13} />
                Select a Target Variable (Y) in the configuration above to start training.
              </span>
            ) : selectedFeatures.length === 0 ? (
              <span className="text-amber-500 font-semibold flex items-center gap-1.5">
                <AlertTriangle size={13} />
                Select at least 1 predictor feature in the Feature Whitelist above.
              </span>
            ) : trainingMode === "tournament" && selectedAlgos.length === 0 ? (
              <span className="text-amber-500 font-semibold flex items-center gap-1.5">
                <AlertTriangle size={13} />
                Select at least 1 algorithm for Tournament Mode.
              </span>
            ) : trainingMode === "tournament" ? (
              <span>Tournament Mode: Benchmarking <strong style={{ color: "var(--txt)" }}>{selectedAlgos.length} common algorithms</strong> with <strong style={{ color: "var(--txt)" }}>{selectedFeatures.length} features</strong> to crown the champion model.</span>
            ) : (
              <span>Manual Mode: Training custom <strong style={{ color: "var(--txt)" }}>{AVAILABLE_ALGORITHMS.find(a => a.id === manualModel)?.name}</strong> with fine-tuned hyperparameters.</span>
            )}
          </div>
        </div>

        <button
          onClick={runAutoml}
          disabled={isTraining || !automlTarget || selectedFeatures.length === 0 || (trainingMode === "tournament" && selectedAlgos.length === 0)}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-xs font-black uppercase tracking-wider text-white transition-all shadow-lg hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
          {isTraining ? (
            <>
              <RefreshCw size={15} className="animate-spin" />
              <span>{trainingMode === "tournament" ? "Running Tournament Benchmark..." : "Fitting Custom Model..."}</span>
            </>
          ) : (
            <>
              <Play size={15} fill="currentColor" />
              <span>{trainingMode === "tournament" ? "Launch Leaderboard Tournament" : `Train Custom ${AVAILABLE_ALGORITHMS.find(a => a.id === manualModel)?.name}`}</span>
            </>
          )}
        </button>
      </div>

      {/* Floating Top-Center Notification */}
      {automlError && (
        <div
          role="alert"
          className="fixed top-5 left-1/2 -translate-x-1/2 z-[99999] w-[92vw] max-w-md px-4 py-3 rounded-xl border shadow-2xl flex items-center justify-between gap-3 bg-red-950/95 border-red-500/50 text-red-200 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-200"
        >
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <AlertCircle size={18} className="shrink-0 text-red-400" />
            <span className="text-xs font-semibold leading-snug break-words">
              {automlError}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setAutomlError("")}
            className="shrink-0 text-red-400 hover:text-red-200 p-1 rounded-md transition-colors cursor-pointer"
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}

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



      {/* -- RESULTS & LEADERBOARD SECTION -- */}
      {automlResult && !isTraining && (
        <div className="space-y-5">
          {/* Mode Banner */}
          {automlResult.mode === "tournament" ? (
            <div className="p-3.5 rounded-xl border flex items-center justify-between flex-wrap gap-2" style={{ background: "linear-gradient(135deg, rgba(245,158,11,0.08), rgba(99,102,241,0.06))", borderColor: "rgba(245,158,11,0.25)" }}>
              <div className="flex items-center gap-2">
                <Trophy size={16} className="text-amber-400" />
                <span className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                  AutoML Tournament Completed: 10 Common Models Evaluated Side-by-Side
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/30">
                  Champion: {automlResult.best_estimator_name || automlResult.best_estimator}
                </span>
              </div>
              <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                Partition: {(automlResult.train_rows || 0).toLocaleString()} train / {(automlResult.test_rows || 0).toLocaleString()} validation rows
              </span>
            </div>
          ) : (
            <div className="p-3.5 rounded-xl border flex items-center justify-between flex-wrap gap-2" style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(59,130,246,0.06))", borderColor: "rgba(99,102,241,0.25)" }}>
              <div className="flex items-center gap-2">
                <SlidersHorizontal size={16} className="text-indigo-400" />
                <span className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                  Manual Tuning Completed: {automlResult.best_estimator_name || AVAILABLE_ALGORITHMS.find(a => a.id === automlResult.selected_model)?.name || automlResult.best_estimator}
                </span>
              </div>
              {automlResult.hyperparameters && (
                <div className="flex items-center gap-1.5 flex-wrap">
                  {Object.entries(automlResult.hyperparameters).map(([k, v]) => (
                    <span key={k} className="text-[9px] font-mono px-1.5 py-0.5 rounded border" style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt-m)" }}>
                      {k}: <strong className="text-indigo-300">{String(v)}</strong>
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
            <div className="p-4 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                {automlResult.mode === "tournament" ? "Champion Architecture" : "Selected Architecture"}
              </p>
              <p className="text-lg font-black font-mono mt-1" style={{ color: "var(--accent)" }}>
                {automlResult.best_estimator_name || automlResult.best_estimator || "Ensemble"}
              </p>
              <p className="text-[10px] mt-0.5 font-mono" style={{ color: "var(--txt-f)" }}>
                Best Loss: {typeof automlResult.best_loss === 'number' ? automlResult.best_loss.toFixed(4) : (automlResult.best_loss ?? "N/A")}
              </p>
            </div>

            <div className="p-4 rounded-2xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <p className="text-[10px] font-mono uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>Training Time</p>
              <p className="text-lg font-black font-mono mt-1" style={{ color: "var(--txt)" }}>
                {automlResult.elapsed_s || automlTimeBudget}s
              </p>
              <p className="text-[10px] mt-0.5 font-mono" style={{ color: "var(--txt-f)" }}>
                Mode: {automlResult.mode === "tournament" ? "10-Model Tournament" : "Manual Hyperparams"}
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
                {automlResult.n_cv_splits ? `${automlResult.n_cv_splits} Splits` : "Validation Holdout"}
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
                <div className="flex items-center gap-2">
                  <Trophy size={14} className="text-amber-400" />
                  <h3 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                    {automlResult.mode === "manual" ? "Tuned Model Performance" : "Tournament Leaderboard"}
                  </h3>
                </div>
                <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                  {automlResult.mode === "manual" ? "1 Model Tuned" : `${(automlResult.leaderboard || []).length} Models Evaluated`}
                </span>
              </div>

              <div className="overflow-x-auto rounded-xl border" style={{ borderColor: "var(--border)" }}>
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="font-mono text-[10px] uppercase tracking-wider" style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)", color: "var(--txt-m)" }}>
                    <tr>
                      <th className="py-2.5 px-3">Rank & Model</th>
                      <th className="py-2.5 px-3">Score</th>
                      <th className="py-2.5 px-3">Latency</th>
                      <th className="py-2.5 px-3">Configuration</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {(automlResult.leaderboard || []).map((row: any, i: number) => {
                      const isFirst = i === 0 || row.best;
                      const isSecond = i === 1 && !row.best;
                      const isThird = i === 2 && !row.best;
                      const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : `#${i + 1}`;

                      return (
                        <tr
                          key={i}
                          style={{ background: isFirst ? "rgba(99,102,241,0.08)" : "transparent" }}>
                          <td className="py-2.5 px-3 font-mono font-bold">
                            <div className="flex items-center gap-2">
                              <span className="w-5 h-5 flex items-center justify-center rounded-md text-[11px] font-mono">
                                {medal}
                              </span>
                              <div>
                                <span style={{ color: isFirst ? "var(--accent)" : "var(--txt)" }}>
                                  {row.display_name || row.model}
                                </span>
                                {isFirst && (
                                  <span className="ml-1.5 text-[8px] font-sans font-bold uppercase tracking-wider px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                    Champion
                                  </span>
                                )}
                              </div>
                            </div>
                          </td>
                          <td className="py-2.5 px-3 font-mono font-bold" style={{ color: isFirst ? "var(--accent)" : "var(--txt)" }}>
                            {typeof row.metric === 'number' ? row.metric.toFixed(4) : (row.metric !== null ? row.metric : "-")}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[10px]" style={{ color: "var(--txt-m)" }}>
                            {row.elapsed_s ? `${Number(row.elapsed_s).toFixed(2)}s` : "-"}
                          </td>
                          <td className="py-2.5 px-3 font-mono text-[10px] max-w-[160px] truncate" style={{ color: "var(--txt-f)" }} title={row.best_config}>
                            {row.best_config || "-"}
                          </td>
                        </tr>
                      );
                    })}
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

          {/* -- Enterprise Model Registry Card -- */}
          <div className="p-5 rounded-2xl border space-y-4" style={{ background: "linear-gradient(135deg, rgba(99,102,241,0.08), rgba(59,130,246,0.04))", borderColor: "rgba(99,102,241,0.25)" }}>
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-md" style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}>
                  <Boxes size={20} className="text-white" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h4 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                      {automlResult.mode === "tournament" ? "Champion Model: " : "Tuned Model: "}
                      <span className="text-indigo-400 font-mono">{automlResult.model_name || customModelName || automlResult.best_estimator_name || automlResult.best_estimator || "Ensemble"}</span>
                    </h4>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      ✓ Registered in Model Catalog
                    </span>
                  </div>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--txt-m)" }}>
                    Trained on {automlResult.train_rows || 0} rows. Manage, test in playground, and apply this model to your dataset in the Models tab.
                  </p>
                </div>
              </div>

              <button
                onClick={() => setActiveTab("models")}
                className="px-5 py-2.5 rounded-xl font-black uppercase tracking-wider text-xs text-white flex items-center gap-2 transition-all hover:scale-[1.02] cursor-pointer shadow-lg"
                style={{ background: "linear-gradient(135deg, #6366f1, #3b82f6)" }}
              >
                <span>Open in Models Section</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>

      )}
    </div>
  );
}
