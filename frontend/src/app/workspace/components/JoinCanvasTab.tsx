"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  GitMerge,
  Database,
  Plus,
  Trash2,
  Play,
  Sparkles,
  Zap,
  Check,
  AlertCircle,
  ArrowRight,
  Upload,
  X,
  Code2,
  Table,
  Layers,
  ChevronDown,
  RefreshCw,
  Copy,
  Sliders,
  Filter,
  BarChart2,
  Terminal,
} from "lucide-react";

interface ColumnSummary {
  name: string;
  dtype: string;
  null_count: number;
  unique_count: number;
  sample_values: any[];
}

interface TableSummary {
  name: string;
  is_primary: boolean;
  row_count: number;
  col_count: number;
  columns: ColumnSummary[];
}

interface InferredRelationship {
  left_table: string;
  left_column: string;
  right_table: string;
  right_column: string;
  confidence: number;
  cardinality: string;
  reason: string;
}

interface JoinCondition {
  left_col: string;
  right_col: string;
  left_table?: string;
}

interface AggregateExpression {
  column: string;
  function: "COUNT" | "SUM" | "AVG" | "MIN" | "MAX" | "COUNT_DISTINCT";
  alias?: string;
}

interface TableRollup {
  table: string;
  group_by: string[];
  aggregates: AggregateExpression[];
}

interface TableFilter {
  table: string;
  column: string;
  operator: "=" | "!=" | ">" | "<" | ">=" | "<=" | "CONTAINS" | "STARTS_WITH" | "ENDS_WITH" | "IS_NULL" | "IS_NOT_NULL" | "IN";
  value: string;
}

interface JoinDefinition {
  table: string;
  join_type: "INNER" | "LEFT" | "RIGHT" | "FULL" | "CROSS" | "SEMI" | "ANTI";
  conditions: JoinCondition[];
  rollup?: TableRollup;
}

interface PreviewResult {
  ok: boolean;
  sql: string;
  columns: { name: string; dtype: string }[];
  rows: any[];
  preview_count: number;
  total_estimated_rows: number;
  execution_time_ms: number;
}

const JOIN_TYPES: {
  id: JoinDefinition["join_type"];
  label: string;
  symbol: string;
  desc: string;
}[] = [
  { id: "LEFT", label: "Left Join", symbol: "◐", desc: "All base rows + matched secondary rows" },
  { id: "INNER", label: "Inner Join", symbol: "∩", desc: "Only rows with matching keys in both" },
  { id: "RIGHT", label: "Right Join", symbol: "◑", desc: "All secondary rows + matched base rows" },
  { id: "FULL", label: "Full Outer", symbol: "◯", desc: "All rows from both tables preserved" },
  { id: "SEMI", label: "Semi Join", symbol: "⊂", desc: "Filter base rows having matching keys in secondary" },
  { id: "ANTI", label: "Anti Join", symbol: "⊄", desc: "Filter base rows with NO match in secondary" },
  { id: "CROSS", label: "Cross Join", symbol: "×", desc: "Cartesian product of all combinations" },
];

const FILTER_OPERATORS: { id: TableFilter["operator"]; label: string }[] = [
  { id: "=", label: "equals (=)" },
  { id: "!=", label: "not equals (!=)" },
  { id: ">", label: "greater than (>)" },
  { id: "<", label: "less than (<)" },
  { id: ">=", label: "greater or equal (>=)" },
  { id: "<=", label: "less or equal (<=)" },
  { id: "CONTAINS", label: "contains" },
  { id: "STARTS_WITH", label: "starts with" },
  { id: "IN", label: "in list (comma separated)" },
  { id: "IS_NULL", label: "is null" },
  { id: "IS_NOT_NULL", label: "is not null" },
];

const AGG_FUNCTIONS: { id: AggregateExpression["function"]; label: string }[] = [
  { id: "SUM", label: "SUM" },
  { id: "COUNT", label: "COUNT" },
  { id: "AVG", label: "AVG" },
  { id: "MIN", label: "MIN" },
  { id: "MAX", label: "MAX" },
  { id: "COUNT_DISTINCT", label: "COUNT DISTINCT" },
];

export function JoinCanvasTab() {
  const { uploadId, setProfile, setCleanProfile, setActiveTab, refreshWorkspace } = useWorkspace();

  // Mode: Visual Builder vs Direct SQL Studio
  const [activeMode, setActiveMode] = useState<"visual" | "sql">("visual");

  // Workspace Tables & Inferred Links
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [relationships, setRelationships] = useState<InferredRelationship[]>([]);
  const [baseTable, setBaseTable] = useState<string>("");
  const [joins, setJoins] = useState<JoinDefinition[]>([]);
  const [filters, setFilters] = useState<TableFilter[]>([]);

  // Rollup Accordion
  const [expandedRollupIdx, setExpandedRollupIdx] = useState<number | null>(null);

  // Custom SQL Studio State
  const [customSql, setCustomSql] = useState<string>("");

  // DuckDB Execution State
  const [previewData, setPreviewData] = useState<PreviewResult | null>(null);
  const [loadingTables, setLoadingTables] = useState<boolean>(false);
  const [executingPreview, setExecutingPreview] = useState<boolean>(false);
  const [materializing, setMaterializing] = useState<boolean>(false);
  const [loadingPreset, setLoadingPreset] = useState<string | null>(null);

  // Modals & Panels
  const [showUploadModal, setShowUploadModal] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTableName, setUploadTableName] = useState<string>("");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [viewingTab, setViewingTab] = useState<"preview" | "sql">("preview");

  // Notifications
  const [statusMessage, setStatusMessage] = useState<{
    type: "success" | "error" | "info";
    text: string;
  } | null>(null);
  const [copiedSql, setCopiedSql] = useState<boolean>(false);

  const showToast = (type: "success" | "error" | "info", text: string) => {
    setStatusMessage({ type, text });
    setTimeout(() => setStatusMessage(null), 5000);
  };

  // --
  // Fetch Tables & Inferred Relations
  // --
  const fetchTables = useCallback(async () => {
    if (!uploadId) return;
    setLoadingTables(true);
    try {
      const res = await apiFetch(`/joins/tables?upload_id=${uploadId}`);
      if (res.ok) {
        const data = await res.json();
        setTables(data.tables || []);
        setRelationships(data.relationships || []);

        if (!baseTable && data.tables?.length > 0) {
          const primary = data.tables.find((t: TableSummary) => t.is_primary) || data.tables[0];
          setBaseTable(primary.name);
          if (!customSql) {
            setCustomSql(`SELECT * FROM "${primary.name}" LIMIT 50;`);
          }
        }
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Failed to load workspace tables.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Network error loading tables.");
    } finally {
      setLoadingTables(false);
    }
  }, [uploadId, baseTable, customSql]);

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  // --
  // 1-Click Relational Preset Loader
  // --
  const handleLoadPreset = async (preset: "ecommerce" | "saas" | "healthcare") => {
    if (!uploadId) {
      showToast("error", "Workspace session not initialized.");
      return;
    }
    setLoadingPreset(preset);
    try {
      const res = await apiFetch("/joins/preset", {
        method: "POST",
        body: JSON.stringify({ upload_id: uploadId, preset }),
      });
      if (res.ok) {
        const data = await res.json();
        setTables(data.tables || []);
        setRelationships(data.relationships || []);

        if (preset === "ecommerce") {
          setBaseTable("customers");
          setJoins([
            {
              table: "orders",
              join_type: "LEFT",
              conditions: [{ left_col: "customer_id", right_col: "customer_id", left_table: "customers" }],
              rollup: {
                table: "orders",
                group_by: ["customer_id"],
                aggregates: [
                  { column: "total_amount", function: "SUM", alias: "lifetime_spend" },
                  { column: "order_id", function: "COUNT", alias: "total_orders" },
                  { column: "total_amount", function: "AVG", alias: "avg_order_value" },
                ],
              },
            },
          ]);
          setFilters([
            {
              table: "customers",
              column: "loyalty_tier",
              operator: "IN",
              value: "Gold, Platinum",
            },
          ]);
          setCustomSql(
            `WITH orders_rollup AS (\n  SELECT customer_id, COUNT(*) AS order_cnt, ROUND(SUM(total_amount), 2) AS total_spent\n  FROM orders\n  GROUP BY customer_id\n)\nSELECT c.*, o.order_cnt, o.total_spent\nFROM customers c\nLEFT JOIN orders_rollup o ON c.customer_id = o.customer_id\nWHERE c.loyalty_tier IN ('Gold', 'Platinum')\nORDER BY o.total_spent DESC;`
          );
        } else if (preset === "saas") {
          setBaseTable("organizations");
          setJoins([
            {
              table: "subscriptions",
              join_type: "LEFT",
              conditions: [{ left_col: "org_id", right_col: "org_id", left_table: "organizations" }],
              rollup: {
                table: "subscriptions",
                group_by: ["org_id"],
                aggregates: [
                  { column: "monthly_revenue", function: "SUM", alias: "mrr_total" },
                  { column: "is_churned", function: "MAX", alias: "has_churned" },
                ],
              },
            },
          ]);
          setFilters([]);
          setCustomSql(
            `SELECT o.org_name, o.industry, s.plan, s.monthly_revenue\nFROM organizations o\nJOIN subscriptions s ON o.org_id = s.org_id\nWHERE s.monthly_revenue > 100\nORDER BY s.monthly_revenue DESC;`
          );
        } else {
          setBaseTable("patients");
          setJoins([
            {
              table: "clinical_visits",
              join_type: "LEFT",
              conditions: [{ left_col: "patient_id", right_col: "patient_id", left_table: "patients" }],
              rollup: {
                table: "clinical_visits",
                group_by: ["patient_id"],
                aggregates: [
                  { column: "visit_id", function: "COUNT", alias: "total_visits" },
                  { column: "systolic_bp", function: "AVG", alias: "avg_systolic" },
                  { column: "glucose_mg_dl", function: "AVG", alias: "avg_glucose" },
                ],
              },
            },
          ]);
          setFilters([
            {
              table: "patients",
              column: "age",
              operator: ">=",
              value: "45",
            },
          ]);
          setCustomSql(
            `SELECT p.patient_id, p.age, p.gender, AVG(v.systolic_bp) as avg_bp, AVG(v.glucose_mg_dl) as avg_glucose\nFROM patients p\nJOIN clinical_visits v ON p.patient_id = v.patient_id\nWHERE p.age >= 45\nGROUP BY p.patient_id, p.age, p.gender\nORDER BY avg_glucose DESC;`
          );
        }

        showToast("success", `Relational schema loaded: ${data.message}`);
        setTimeout(() => handlePreview(true), 300);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Failed to load relational preset.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Failed to connect to backend.");
    } finally {
      setLoadingPreset(null);
    }
  };

  // --
  // Upload Secondary Table
  // --
  const handleUploadTable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !uploadId) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("upload_id", uploadId);
    if (uploadTableName.trim()) {
      formData.append("table_name", uploadTableName.trim());
    }
    formData.append("file", uploadFile);

    try {
      const res = await apiFetch("/joins/tables/upload", {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        setTables(data.tables || []);
        setRelationships(data.relationships || []);
        setShowUploadModal(false);
        setUploadFile(null);
        setUploadTableName("");
        showToast("success", data.message || "Table uploaded successfully.");
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Table upload failed.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Network error uploading table.");
    } finally {
      setIsUploading(false);
    }
  };

  // --
  // Delete Secondary Table
  // --
  const handleDeleteTable = async (tableName: string) => {
    if (!uploadId) return;

    try {
      const res = await apiFetch(`/joins/tables/${tableName}?upload_id=${uploadId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        const data = await res.json();
        setTables(data.tables || []);
        setRelationships(data.relationships || []);
        setJoins((prev) => prev.filter((j) => j.table !== tableName));
        if (baseTable === tableName && data.tables?.length > 0) {
          setBaseTable(data.tables[0].name);
        }
        showToast("info", `Table "${tableName}" removed.`);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Failed to delete table.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Failed to delete table.");
    }
  };

  // --
  // DuckDB Pushdown Preview Execution
  // --
  const handlePreview = async (silent = false) => {
    if (!uploadId) return;

    setExecutingPreview(true);
    try {
      let res;
      if (activeMode === "sql") {
        if (!customSql.trim()) {
          showToast("info", "Please enter a SQL query.");
          setExecutingPreview(false);
          return;
        }
        res = await apiFetch("/joins/sql/preview", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            sql: customSql,
            limit: 50,
          }),
        });
      } else {
        if (!baseTable) {
          if (!silent) showToast("info", "Please select a base table.");
          setExecutingPreview(false);
          return;
        }
        res = await apiFetch("/joins/preview", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            base_table: baseTable,
            joins: joins,
            filters: filters.filter((f) => f.column && (f.operator.includes("NULL") || f.value)),
            limit: 50,
          }),
        });
      }

      if (res.ok) {
        const data: PreviewResult = await res.json();
        setPreviewData(data);
        if (activeMode === "visual" && data.sql) {
          setCustomSql(data.sql);
        }
        if (!silent) {
          showToast(
            "success",
            `DuckDB executed query in ${data.execution_time_ms} ms (${data.total_estimated_rows.toLocaleString()} estimated rows)`
          );
        }
      } else {
        const err = await res.json().catch(() => ({}));
        if (!silent) showToast("error", err.detail || "DuckDB execution failed.");
      }
    } catch (e: any) {
      if (!silent) showToast("error", e.message || "Failed to execute DuckDB preview.");
    } finally {
      setExecutingPreview(false);
    }
  };

  // --
  // Materialize Join into Workspace Dataset
  // --
  const handleMaterialize = async () => {
    if (!uploadId) return;

    setMaterializing(true);
    try {
      let res;
      if (activeMode === "sql") {
        res = await apiFetch("/joins/sql/materialize", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            sql: customSql,
            output_dataset_name: "custom_sql_materialized.csv",
          }),
        });
      } else {
        if (!baseTable) {
          showToast("error", "No table selected.");
          setMaterializing(false);
          return;
        }
        res = await apiFetch("/joins/materialize", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            base_table: baseTable,
            joins: joins,
            filters: filters.filter((f) => f.column && (f.operator.includes("NULL") || f.value)),
            output_dataset_name: `merged_${baseTable}.csv`,
          }),
        });
      }

      if (res.ok) {
        const data = await res.json();
        if (data.profile) {
          setProfile(data.profile);
          setCleanProfile(data.profile);
        }
        if (refreshWorkspace) {
          await refreshWorkspace(uploadId);
        }
        showToast("success", `⚡ ${data.message}`);
        setTimeout(() => {
          setActiveTab("cleaning");
        }, 1200);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Materialization failed.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Failed to materialize dataset.");
    } finally {
      setMaterializing(false);
    }
  };

  // --
  // Join Pipeline & Rollup Management
  // --
  const addJoinStep = (targetTable: string) => {
    const inferred = relationships.find(
      (r) =>
        (r.left_table === baseTable && r.right_table === targetTable) ||
        (r.right_table === baseTable && r.left_table === targetTable)
    );

    let initialCond: JoinCondition = { left_col: "", right_col: "", left_table: baseTable };
    if (inferred) {
      if (inferred.left_table === baseTable) {
        initialCond = { left_col: inferred.left_column, right_col: inferred.right_column, left_table: baseTable };
      } else {
        initialCond = { left_col: inferred.right_column, right_col: inferred.left_column, left_table: baseTable };
      }
    } else {
      const baseObj = tables.find((t) => t.name === baseTable);
      const targetObj = tables.find((t) => t.name === targetTable);
      if (baseObj?.columns?.length && targetObj?.columns?.length) {
        initialCond = { left_col: baseObj.columns[0].name, right_col: targetObj.columns[0].name, left_table: baseTable };
      }
    }

    setJoins((prev) => [
      ...prev,
      {
        table: targetTable,
        join_type: "LEFT",
        conditions: [initialCond],
      },
    ]);
  };

  const removeJoinStep = (index: number) => {
    setJoins((prev) => prev.filter((_, i) => i !== index));
    if (expandedRollupIdx === index) setExpandedRollupIdx(null);
  };

  const updateJoinType = (index: number, joinType: JoinDefinition["join_type"]) => {
    setJoins((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], join_type: joinType };
      return next;
    });
  };

  const updateCondition = (
    joinIdx: number,
    condIdx: number,
    field: "left_col" | "right_col" | "left_table",
    val: string
  ) => {
    setJoins((prev) => {
      const next = [...prev];
      const conds = [...next[joinIdx].conditions];
      conds[condIdx] = { ...conds[condIdx], [field]: val };
      next[joinIdx] = { ...next[joinIdx], conditions: conds };
      return next;
    });
  };

  // Rollup Helpers
  const toggleRollup = (idx: number) => {
    setJoins((prev) => {
      const next = [...prev];
      const target = next[idx];
      if (target.rollup) {
        // disable rollup
        delete target.rollup;
      } else {
        // initialize rollup
        const condKey = target.conditions[0]?.right_col || "id";
        const targetObj = tables.find((t) => t.name === target.table);
        const numericCol = targetObj?.columns.find((c) =>
          c.dtype.toLowerCase().includes("int") || c.dtype.toLowerCase().includes("float")
        )?.name || condKey;

        target.rollup = {
          table: target.table,
          group_by: [condKey],
          aggregates: [
            { column: numericCol, function: "SUM", alias: `${target.table}_total` },
            { column: condKey, function: "COUNT", alias: `${target.table}_count` },
          ],
        };
      }
      return next;
    });
    setExpandedRollupIdx(expandedRollupIdx === idx ? null : idx);
  };

  const addRollupMetric = (joinIdx: number) => {
    setJoins((prev) => {
      const next = [...prev];
      const target = next[joinIdx];
      if (!target.rollup) return prev;
      const targetObj = tables.find((t) => t.name === target.table);
      const colName = targetObj?.columns[0]?.name || "id";
      target.rollup.aggregates.push({
        column: colName,
        function: "COUNT",
        alias: `${target.table}_metric_${target.rollup.aggregates.length + 1}`,
      });
      return next;
    });
  };

  const removeRollupMetric = (joinIdx: number, mIdx: number) => {
    setJoins((prev) => {
      const next = [...prev];
      const target = next[joinIdx];
      if (!target.rollup) return prev;
      target.rollup.aggregates = target.rollup.aggregates.filter((_, i) => i !== mIdx);
      return next;
    });
  };

  const updateRollupMetric = (
    joinIdx: number,
    mIdx: number,
    field: "column" | "function" | "alias",
    val: string
  ) => {
    setJoins((prev) => {
      const next = [...prev];
      const target = next[joinIdx];
      if (!target.rollup) return prev;
      target.rollup.aggregates[mIdx] = {
        ...target.rollup.aggregates[mIdx],
        [field]: val,
      };
      return next;
    });
  };

  // --
  // Filter Management
  // --
  const addFilter = () => {
    const defaultTable = baseTable || (tables[0]?.name ?? "primary_table");
    const tableObj = tables.find((t) => t.name === defaultTable) || tables[0];
    const defaultCol = tableObj?.columns[0]?.name || "id";

    setFilters((prev) => [
      ...prev,
      {
        table: defaultTable,
        column: defaultCol,
        operator: "=",
        value: "",
      },
    ]);
  };

  const removeFilter = (idx: number) => {
    setFilters((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateFilter = (idx: number, field: keyof TableFilter, val: string) => {
    setFilters((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], [field]: val };
      return next;
    });
  };

  const applyInferred = (inf: InferredRelationship) => {
    if (baseTable !== inf.left_table && baseTable !== inf.right_table) {
      setBaseTable(inf.left_table);
    }
    const currentBase = baseTable === inf.right_table ? inf.right_table : inf.left_table;
    const target = currentBase === inf.left_table ? inf.right_table : inf.left_table;
    const leftCol = currentBase === inf.left_table ? inf.left_column : inf.right_column;
    const rightCol = currentBase === inf.left_table ? inf.right_column : inf.left_column;

    const existingIdx = joins.findIndex((j) => j.table === target);
    if (existingIdx >= 0) {
      updateCondition(existingIdx, 0, "left_col", leftCol);
      updateCondition(existingIdx, 0, "right_col", rightCol);
    } else {
      setJoins((prev) => [
        ...prev,
        {
          table: target,
          join_type: "LEFT",
          conditions: [{ left_col: leftCol, right_col: rightCol, left_table: currentBase }],
        },
      ]);
    }
    showToast("success", `Wired: ${currentBase}.${leftCol} = ${target}.${rightCol}`);
  };

  const availableSecondaryTables = tables.filter(
    (t) => t.name !== baseTable && !joins.some((j) => j.table === t.name)
  );

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: "var(--bg)", color: "var(--txt)" }}>
      {/* -- TOP ACTION BAR ---- */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b shrink-0"
        style={{ background: "var(--card-bg, rgba(20,20,25,0.4))", borderColor: "var(--border)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center font-bold"
            style={{
              background: "linear-gradient(135deg, rgba(255, 67, 16, 0.2), rgba(99, 102, 241, 0.2))",
              border: "1px solid rgba(255, 67, 16, 0.3)",
              color: "var(--accent)",
            }}
          >
            <GitMerge size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-black tracking-tight" style={{ color: "var(--txt)" }}>
                Combine &amp; Link Data Tables
              </h1>
              <span
                className="px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider"
                style={{
                  background: "var(--glow)",
                  color: "var(--accent)",
                  border: "1px solid var(--accent)",
                }}
              >
                Smart Link Engine
              </span>
            </div>
            <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
              Easily merge datasets together (e.g. attach customer info to transactions) without writing any code.
            </p>
          </div>

        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Mode Switcher */}
          <div
            className="flex items-center p-0.5 rounded-xl border text-[11px] font-bold"
            style={{ borderColor: "var(--border)", background: "var(--input-bg, rgba(255,255,255,0.03))" }}
          >
            <button
              onClick={() => setActiveMode("visual")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition ${
                activeMode === "visual"
                  ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Sliders size={12} />
              <span>Visual Canvas</span>
            </button>
            <button
              onClick={() => setActiveMode("sql")}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition ${
                activeMode === "sql"
                  ? "bg-indigo-600/30 text-indigo-300 border border-indigo-500/50 shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Terminal size={12} />
              <span>SQL Studio</span>
            </button>
          </div>

          {/* Quick Presets */}
          <div
            className="hidden xl:flex items-center gap-1 p-1 rounded-xl border text-[11px]"
            style={{ borderColor: "var(--border)", background: "var(--input-bg, rgba(255,255,255,0.03))" }}
          >
            <span className="px-2 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
              Presets:
            </span>
            <button
              onClick={() => handleLoadPreset("ecommerce")}
              disabled={loadingPreset !== null}
              className="px-2 py-1 rounded-lg font-semibold transition hover:opacity-80 disabled:opacity-50"
              style={{
                background: loadingPreset === "ecommerce" ? "var(--accent)" : "transparent",
                color: loadingPreset === "ecommerce" ? "#fff" : "var(--txt)",
              }}
            >
              🛒 E-Commerce
            </button>
            <button
              onClick={() => handleLoadPreset("saas")}
              disabled={loadingPreset !== null}
              className="px-2 py-1 rounded-lg font-semibold transition hover:opacity-80 disabled:opacity-50"
              style={{
                background: loadingPreset === "saas" ? "var(--accent)" : "transparent",
                color: loadingPreset === "saas" ? "#fff" : "var(--txt)",
              }}
            >
              🏢 SaaS
            </button>
            <button
              onClick={() => handleLoadPreset("healthcare")}
              disabled={loadingPreset !== null}
              className="px-2 py-1 rounded-lg font-semibold transition hover:opacity-80 disabled:opacity-50"
              style={{
                background: loadingPreset === "healthcare" ? "var(--accent)" : "transparent",
                color: loadingPreset === "healthcare" ? "#fff" : "var(--txt)",
              }}
            >
              🏥 Healthcare
            </button>
          </div>

          {/* Add Table */}
          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition hover:scale-[1.02] cursor-pointer"
            style={{
              background: "rgba(255,255,255,0.04)",
              borderColor: "var(--border)",
              color: "var(--txt)",
            }}
          >
            <Plus size={13} />
            <span>Add Table</span>
          </button>

          {/* Run Preview */}
          <button
            onClick={() => handlePreview()}
            disabled={executingPreview || (!baseTable && activeMode === "visual")}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition hover:scale-[1.02] disabled:opacity-50 cursor-pointer"
            style={{
              background: "rgba(99, 102, 241, 0.15)",
              border: "1px solid rgba(99, 102, 241, 0.4)",
              color: "#818cf8",
            }}
          >
            <Play size={13} className={executingPreview ? "animate-spin" : ""} />
            <span>{executingPreview ? "Running..." : "Run Preview"}</span>
          </button>

          {/* Materialize into Workspace */}
          <button
            onClick={handleMaterialize}
            disabled={materializing || (!baseTable && activeMode === "visual")}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold transition shadow-lg hover:scale-[1.02] disabled:opacity-50 cursor-pointer"
            style={{
              background: "linear-gradient(135deg, var(--accent), #ff7043)",
              color: "#fff",
            }}
          >
            <Zap size={13} className={materializing ? "animate-bounce" : ""} />
            <span>{materializing ? "Materializing..." : "Materialize"}</span>
          </button>
        </div>
      </div>

      {/* -- TOAST STATUS ---- */}
      {statusMessage && (
        <div
          className={`mx-5 mt-3 px-4 py-2.5 rounded-xl text-xs font-medium flex items-center justify-between border transition-all ${
            statusMessage.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              : statusMessage.type === "error"
              ? "bg-rose-500/10 border-rose-500/30 text-rose-400"
              : "bg-blue-500/10 border-blue-500/30 text-blue-400"
          }`}
        >
          <div className="flex items-center gap-2">
            {statusMessage.type === "success" ? <Check size={14} /> : <AlertCircle size={14} />}
            <span>{statusMessage.text}</span>
          </div>
          <button onClick={() => setStatusMessage(null)} className="hover:opacity-75">
            <X size={12} />
          </button>
        </div>
      )}

      {/* -- INFERRED RELATIONSHIPS BAR ---- */}
      {relationships.length > 0 && activeMode === "visual" && (
        <div
          className="mx-5 mt-3 p-3 rounded-2xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-3 shrink-0"
          style={{
            background: "linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(255, 67, 16, 0.05))",
            borderColor: "rgba(99, 102, 241, 0.25)",
          }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
              style={{ background: "rgba(99, 102, 241, 0.2)", color: "#818cf8" }}
            >
              <Sparkles size={14} />
            </div>
            <div>
              <div className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                Inferred Schema Relationships ({relationships.length} detected)
              </div>
              <div className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                Click to wire key foreign keys directly into your join canvas.
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {relationships.slice(0, 3).map((r, i) => (
              <button
                key={i}
                onClick={() => applyInferred(r)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold border transition hover:scale-[1.02] cursor-pointer"
                style={{
                  background: "rgba(99, 102, 241, 0.12)",
                  borderColor: "rgba(99, 102, 241, 0.3)",
                  color: "#a5b4fc",
                }}
                title={r.reason}
              >
                <span>
                  {r.left_table}.{r.left_column} ↔ {r.right_table}.{r.right_column}
                </span>
                <span
                  className="px-1 py-0.5 rounded text-[8px] uppercase tracking-wider font-black"
                  style={{ background: "rgba(16, 185, 129, 0.2)", color: "#10b981" }}
                >
                  {Math.round(r.confidence * 100)}%
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* -- WORKSPACE SPLIT VIEW ---- */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden p-5 gap-5">
        {/* -- LEFT PANEL: CONFIGURATION OR SQL STUDIO ---- */}
        <div className="flex-1 flex flex-col gap-4 overflow-y-auto pr-1">
          {activeMode === "visual" ? (
            <>
              {/* 1. Base Table Selector */}
              <div
                className="p-4 rounded-2xl border"
                style={{ background: "var(--card-bg, rgba(20,20,25,0.6))", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs"
                      style={{ background: "var(--accent)", color: "#fff" }}
                    >
                      1
                    </div>
                    <h3 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                      Base Table (FROM)
                    </h3>
                  </div>
                  <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                    {tables.length} tables in workspace
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {tables.map((t) => (
                    <button
                      key={t.name}
                      onClick={() => {
                        setBaseTable(t.name);
                        setJoins((prev) => prev.filter((j) => j.table !== t.name));
                      }}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold border transition ${
                        baseTable === t.name
                          ? "ring-2 ring-[var(--accent)] border-[var(--accent)] shadow-md"
                          : "hover:border-zinc-500 opacity-80"
                      }`}
                      style={{
                        background:
                          baseTable === t.name
                            ? "rgba(255, 67, 16, 0.12)"
                            : "var(--input-bg, rgba(255,255,255,0.02))",
                        borderColor: baseTable === t.name ? "var(--accent)" : "var(--border)",
                        color: "var(--txt)",
                      }}
                    >
                      <Database size={13} style={{ color: "var(--accent)" }} />
                      <span>{t.name}</span>
                      <span
                        className="px-1.5 py-0.5 rounded text-[9px] font-mono"
                        style={{ background: "rgba(255,255,255,0.06)", color: "var(--txt-m)" }}
                      >
                        {t.row_count.toLocaleString()} rows
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. Join Pipeline Cards */}
              <div className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs"
                      style={{ background: "#6366f1", color: "#fff" }}
                    >
                      2
                    </div>
                    <h3 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                      Relational Joins & Pre-Join Rollups ({joins.length})
                    </h3>
                  </div>

                  {availableSecondaryTables.length > 0 && (
                    <div className="relative group">
                      <button
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold border transition hover:opacity-80"
                        style={{
                          background: "rgba(99, 102, 241, 0.1)",
                          borderColor: "rgba(99, 102, 241, 0.3)",
                          color: "#818cf8",
                        }}
                      >
                        <Plus size={12} />
                        <span>Join Table</span>
                        <ChevronDown size={11} />
                      </button>

                      <div
                        className="absolute right-0 top-full mt-1 w-48 py-1 rounded-xl shadow-2xl border hidden group-hover:block z-20"
                        style={{ background: "var(--nav)", borderColor: "var(--border)" }}
                      >
                        {availableSecondaryTables.map((t) => (
                          <button
                            key={t.name}
                            onClick={() => addJoinStep(t.name)}
                            className="w-full px-3 py-2 text-left text-xs flex items-center justify-between transition-colors cursor-pointer"
                            style={{ color: "var(--txt)" }}
                          >
                            <span className="font-bold">{t.name}</span>
                            <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                              {t.row_count.toLocaleString()} rows
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {joins.length === 0 ? (
                  <div
                    className="p-6 rounded-2xl border text-center flex flex-col items-center justify-center gap-3"
                    style={{
                      background: "var(--card-bg, rgba(20,20,25,0.3))",
                      borderColor: "var(--border)",
                      borderStyle: "dashed",
                    }}
                  >
                    <Layers size={28} style={{ color: "var(--txt-m)" }} />
                    <div className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                      No Joins Configured Yet
                    </div>
                    <p className="text-[11px] max-w-sm" style={{ color: "var(--txt-m)" }}>
                      Combine {baseTable || "the base table"} with another dataset using Left, Inner, Right, or Full Outer joins.
                    </p>
                    {availableSecondaryTables.length > 0 ? (
                      <button
                        onClick={() => addJoinStep(availableSecondaryTables[0].name)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition hover:scale-[1.02] cursor-pointer"
                        style={{
                          background: "var(--accent)",
                          borderColor: "var(--accent)",
                          color: "#fff",
                        }}
                      >
                        <Plus size={12} />
                        <span>Join with {availableSecondaryTables[0].name}</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => setShowUploadModal(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border transition hover:scale-[1.02] cursor-pointer"
                        style={{
                          background: "var(--accent)",
                          borderColor: "var(--accent)",
                          color: "#fff",
                        }}
                      >
                        <Plus size={12} />
                        <span>Add Second Table to Join</span>
                      </button>
                    )}
                  </div>
                ) : (
                  joins.map((j, idx) => {
                    const targetObj = tables.find((t) => t.name === j.table);
                    const baseObj = tables.find((t) => t.name === (j.conditions[0]?.left_table || baseTable));
                    const isRollupOpen = expandedRollupIdx === idx;

                    return (
                      <div
                        key={idx}
                        className="p-4 rounded-2xl border flex flex-col gap-3 relative transition"
                        style={{
                          background: "var(--card-bg, rgba(20,20,25,0.6))",
                          borderColor: "var(--border)",
                        }}
                      >
                        {/* Header */}
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span
                              className="px-2 py-0.5 rounded text-[10px] font-mono font-bold"
                              style={{ background: "rgba(99,102,241,0.15)", color: "#818cf8" }}
                            >
                              Step {idx + 1}
                            </span>
                            <div className="flex items-center gap-1.5 text-xs font-bold">
                              <span>{j.conditions[0]?.left_table || baseTable}</span>
                              <ArrowRight size={12} className="text-zinc-500" />
                              <span style={{ color: "var(--accent)" }}>{j.table}</span>
                              {j.rollup && (
                                <span className="px-1.5 py-0.2 rounded text-[8px] font-black uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                  Aggregated (CTE)
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-1">
                            {/* Pre-Join Rollup Toggle Button */}
                            <button
                              onClick={() => toggleRollup(idx)}
                              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold border transition ${
                                j.rollup
                                  ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                                  : "border-[var(--border)] text-[var(--txt-m)] hover:text-[var(--txt)]"
                              }`}
                              title="Aggregate secondary table before joining (GROUP BY + SUM/COUNT/AVG)"
                            >
                              <BarChart2 size={11} />
                              <span>{j.rollup ? "Rollup Active" : "+ Pre-Join Rollup"}</span>
                            </button>

                            <button
                              onClick={() => removeJoinStep(idx)}
                              className="p-1 rounded-lg hover:bg-rose-500/10 text-zinc-400 hover:text-rose-400 transition"
                              title="Remove join step"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>

                        {/* Join Type Chips */}
                        <div className="flex flex-wrap items-center gap-1.5">
                          {JOIN_TYPES.map((jt) => (
                            <button
                              key={jt.id}
                              onClick={() => updateJoinType(idx, jt.id)}
                              className={`px-2 py-0.5 rounded-lg text-[10px] font-bold border transition flex items-center gap-1 ${
                                j.join_type === jt.id
                                  ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 ring-1 ring-indigo-500"
                                  : "border-zinc-800 hover:border-zinc-600 text-zinc-400"
                              }`}
                              title={jt.desc}
                            >
                              <span>{jt.symbol}</span>
                              <span>{jt.label}</span>
                            </button>
                          ))}
                        </div>

                        {/* Join Condition Inputs */}
                        {j.conditions.map((cond, cIdx) => (
                          <div
                            key={cIdx}
                            className="p-2.5 rounded-xl border flex flex-wrap items-center gap-2 text-xs"
                            style={{
                              background: "var(--input-bg, rgba(255,255,255,0.02))",
                              borderColor: "var(--border)",
                            }}
                          >
                            <span className="text-[10px] font-mono text-zinc-400">ON</span>
                            <div className="flex items-center gap-1">
                              <span className="text-[10px] font-bold text-zinc-300">
                                {cond.left_table || baseTable}.
                              </span>
                              <select
                                value={cond.left_col}
                                onChange={(e) => updateCondition(idx, cIdx, "left_col", e.target.value)}
                                className="border rounded-lg px-2.5 py-1 text-xs font-mono font-medium focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                style={{
                                  background: "var(--inp-bg)",
                                  borderColor: "var(--border)",
                                  color: "var(--txt)",
                                }}
                              >
                                <option value="" disabled>Select Key</option>
                                {baseObj?.columns.map((c) => (
                                  <option key={c.name} value={c.name}>
                                    {c.name} ({c.dtype})
                                  </option>
                                ))}
                              </select>
                            </div>

                            <span className="font-bold" style={{ color: "var(--txt-m)" }}>=</span>

                            <div className="flex items-center gap-1">
                              <span className="text-[10px] font-bold" style={{ color: "var(--txt-m)" }}>{j.table}.</span>
                              <select
                                value={cond.right_col}
                                onChange={(e) => updateCondition(idx, cIdx, "right_col", e.target.value)}
                                className="border rounded-lg px-2.5 py-1 text-xs font-mono font-medium focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                style={{
                                  background: "var(--inp-bg)",
                                  borderColor: "var(--border)",
                                  color: "var(--txt)",
                                }}
                              >
                                <option value="" disabled>Select Key</option>
                                {targetObj?.columns.map((c) => (
                                  <option key={c.name} value={c.name}>
                                    {c.name} ({c.dtype})
                                  </option>
                                ))}
                              </select>
                            </div>

                          </div>
                        ))}

                        {/* Rollup Configuration Section */}
                        {j.rollup && isRollupOpen && (
                          <div
                            className="p-3 rounded-xl border mt-1 flex flex-col gap-2.5"
                            style={{
                              background: "rgba(16, 185, 129, 0.04)",
                              borderColor: "rgba(16, 185, 129, 0.25)",
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-400">
                                <BarChart2 size={13} />
                                <span>Pre-Join Group By & Aggregation Rollup</span>
                              </div>
                              <button
                                onClick={() => addRollupMetric(idx)}
                                className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
                              >
                                <Plus size={11} />
                                <span>Add Metric</span>
                              </button>
                            </div>

                            {/* Group By selector */}
                            <div className="flex items-center gap-2 text-xs">
                              <span className="text-[10px] font-mono text-zinc-400">GROUP BY:</span>
                              <select
                                value={j.rollup.group_by[0] || ""}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setJoins((prev) => {
                                    const next = [...prev];
                                    if (next[idx].rollup) {
                                      next[idx].rollup!.group_by = [val];
                                    }
                                    return next;
                                  });
                                }}
                                className="border rounded-lg px-2.5 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                style={{
                                  background: "var(--inp-bg)",
                                  borderColor: "var(--border)",
                                  color: "var(--txt)",
                                }}
                              >
                                {targetObj?.columns.map((c) => (
                                  <option key={c.name} value={c.name}>
                                    {c.name}
                                  </option>
                                ))}
                              </select>
                            </div>

                            {/* Metrics list */}
                            <div className="space-y-1.5">
                              {j.rollup.aggregates.map((agg, mIdx) => (
                                <div key={mIdx} className="flex items-center gap-2 text-xs">
                                  <select
                                    value={agg.function}
                                    onChange={(e) => updateRollupMetric(idx, mIdx, "function", e.target.value)}
                                    className="border rounded-lg px-2 py-1 text-xs font-mono font-bold focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                    style={{
                                      background: "var(--inp-bg)",
                                      borderColor: "var(--border)",
                                      color: "var(--accent)",
                                    }}
                                  >
                                    {AGG_FUNCTIONS.map((f) => (
                                      <option key={f.id} value={f.id}>
                                        {f.label}
                                      </option>
                                    ))}
                                  </select>

                                  <select
                                    value={agg.column}
                                    onChange={(e) => updateRollupMetric(idx, mIdx, "column", e.target.value)}
                                    className="border rounded-lg px-2 py-1 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                    style={{
                                      background: "var(--inp-bg)",
                                      borderColor: "var(--border)",
                                      color: "var(--txt)",
                                    }}
                                  >
                                    {targetObj?.columns.map((c) => (
                                      <option key={c.name} value={c.name}>
                                        {c.name}
                                      </option>
                                    ))}
                                  </select>

                                  <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>AS</span>

                                  <input
                                    type="text"
                                    value={agg.alias || ""}
                                    placeholder="metric_alias"
                                    onChange={(e) => updateRollupMetric(idx, mIdx, "alias", e.target.value)}
                                    className="border rounded-lg px-2 py-1 text-xs font-mono flex-1 min-w-0 focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                    style={{
                                      background: "var(--inp-bg)",
                                      borderColor: "var(--border)",
                                      color: "var(--txt)",
                                    }}
                                  />


                                  <button
                                    onClick={() => removeRollupMetric(idx, mIdx)}
                                    className="p-1 text-zinc-500 hover:text-rose-400"
                                    title="Delete metric"
                                  >
                                    <Trash2 size={11} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>

              {/* 3. Custom Filters (WHERE Clause) */}
              <div
                className="p-4 rounded-2xl border flex flex-col gap-3"
                style={{ background: "var(--card-bg, rgba(20,20,25,0.6))", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-6 h-6 rounded-md flex items-center justify-center font-bold text-xs"
                      style={{ background: "#f59e0b", color: "#fff" }}
                    >
                      3
                    </div>
                    <h3 className="text-xs font-black uppercase tracking-wider" style={{ color: "var(--txt)" }}>
                      Custom Filters (WHERE Clauses)
                    </h3>
                  </div>

                  <button
                    onClick={addFilter}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold border transition hover:opacity-80"
                    style={{
                      background: "rgba(245, 158, 11, 0.1)",
                      borderColor: "rgba(245, 158, 11, 0.3)",
                      color: "#fbbf24",
                    }}
                  >
                    <Plus size={12} />
                    <span>Add Filter</span>
                  </button>
                </div>

                {filters.length === 0 ? (
                  <p className="text-[11px] text-zinc-500 italic">
                    No filters defined. Output contains all joined rows.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {filters.map((f, fIdx) => {
                      const curTableObj = tables.find((t) => t.name === f.table) || tables[0];

                      return (
                        <div
                          key={fIdx}
                          className="p-2.5 rounded-xl border flex flex-wrap items-center gap-2 text-xs"
                          style={{
                            background: "var(--input-bg, rgba(255,255,255,0.02))",
                            borderColor: "var(--border)",
                          }}
                        >
                          <select
                            value={f.table}
                            onChange={(e) => updateFilter(fIdx, "table", e.target.value)}
                            className="rounded-lg px-2.5 py-1.5 text-xs font-mono font-bold border transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                            style={{
                              background: "var(--inp-bg)",
                              borderColor: "var(--border)",
                              color: "var(--txt)",
                            }}
                          >
                            {tables.map((t) => (
                              <option key={t.name} value={t.name}>
                                {t.name}
                              </option>
                            ))}
                          </select>

                          <select
                            value={f.column}
                            onChange={(e) => updateFilter(fIdx, "column", e.target.value)}
                            className="rounded-lg px-2.5 py-1.5 text-xs font-mono border transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                            style={{
                              background: "var(--inp-bg)",
                              borderColor: "var(--border)",
                              color: "var(--txt)",
                            }}
                          >
                            {curTableObj?.columns.map((c) => (
                              <option key={c.name} value={c.name}>
                                {c.name}
                              </option>
                            ))}
                          </select>

                          <select
                            value={f.operator}
                            onChange={(e) => updateFilter(fIdx, "operator", e.target.value as TableFilter["operator"])}
                            className="rounded-lg px-2.5 py-1.5 text-xs font-mono font-semibold border transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                            style={{
                              background: "var(--inp-bg)",
                              borderColor: "var(--border)",
                              color: "var(--accent)",
                            }}
                          >
                            {FILTER_OPERATORS.map((op) => (
                              <option key={op.id} value={op.id}>
                                {op.label}
                              </option>
                            ))}
                          </select>

                          {!f.operator.includes("NULL") && (
                            <input
                              type="text"
                              value={f.value}
                              placeholder="Value or comma list"
                              onChange={(e) => updateFilter(fIdx, "value", e.target.value)}
                              className="rounded-lg px-2.5 py-1.5 text-xs font-mono flex-1 min-w-[120px] border transition-colors focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                              style={{
                                background: "var(--inp-bg)",
                                borderColor: "var(--border)",
                                color: "var(--txt)",
                              }}
                            />
                          )}


                          <button
                            onClick={() => removeFilter(fIdx)}
                            className="p-1 text-zinc-500 hover:text-rose-400"
                            title="Delete filter"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          ) : (
            /* -- DIRECT SQL STUDIO (MODE: SQL) ---- */
            <div
              className="p-4 rounded-2xl border flex flex-col gap-3 h-full"
              style={{ background: "var(--card-bg, rgba(20,20,25,0.6))", borderColor: "var(--border)" }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal size={16} className="text-indigo-400" />
                  <h3 className="text-xs font-black uppercase tracking-wider">
                    Direct DuckDB SQL Studio (In-Memory Catalog)
                  </h3>
                </div>

                <div className="flex items-center gap-1.5 text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                  <span>Registered:</span>
                  {tables.map((t) => (
                    <span
                      key={t.name}
                      className="px-1.5 py-0.5 rounded font-bold border"
                      style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--accent)" }}
                    >
                      {t.name}
                    </span>
                  ))}
                </div>
              </div>

              {/* Quick Snippet Chips */}
              <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                <span style={{ color: "var(--txt-f)" }}>Snippets:</span>
                <button
                  onClick={() =>
                    setCustomSql(
                      `SELECT loyalty_tier, COUNT(*) as cust_cnt, ROUND(AVG(total_amount), 2) as avg_spent\nFROM customers c\nJOIN orders o ON c.customer_id = o.customer_id\nGROUP BY loyalty_tier\nORDER BY avg_spent DESC;`
                    )
                  }
                  className="px-2 py-0.5 rounded border transition cursor-pointer"
                  style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                >
                  Cohort Aggregation
                </button>
                <button
                  onClick={() =>
                    setCustomSql(
                      `SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) as order_rank\nFROM orders;`
                    )
                  }
                  className="px-2 py-0.5 rounded border transition cursor-pointer"
                  style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                >
                  Window Function (Rank)
                </button>
                <button
                  onClick={() =>
                    setCustomSql(
                      `SELECT * FROM orders\nWHERE total_amount > (SELECT AVG(total_amount) FROM orders)\nORDER BY total_amount DESC;`
                    )
                  }
                  className="px-2 py-0.5 rounded border transition cursor-pointer"
                  style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                >
                  Subquery Filter
                </button>
              </div>

              {/* SQL Textarea */}
              <div className="flex-1 min-h-[220px] relative">
                <textarea
                  value={customSql}
                  onChange={(e) => setCustomSql(e.target.value)}
                  placeholder="Write arbitrary DuckDB SQL (e.g. SELECT * FROM orders JOIN customers...)"
                  className="w-full h-full p-4 rounded-xl border font-mono text-xs leading-relaxed focus:outline-none focus:border-indigo-500 resize-none"
                  style={{
                    background: "#0d1117",
                    borderColor: "var(--border)",
                    color: "#58a6ff",
                  }}
                  spellCheck={false}
                />
              </div>
            </div>
          )}
        </div>

        {/* -- RIGHT PANEL: DUCKDB RESULTS & LIVE SQL VIEW ---- */}
        <div
          className="flex-1 flex flex-col rounded-2xl border overflow-hidden"
          style={{ background: "var(--card-bg, rgba(20,20,25,0.6))", borderColor: "var(--border)" }}
        >
          {/* Subheader / Tabs */}
          <div
            className="flex items-center justify-between px-4 py-2.5 border-b shrink-0"
            style={{ borderColor: "var(--border)", background: "rgba(0,0,0,0.15)" }}
          >
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewingTab("preview")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold transition ${
                  viewingTab === "preview"
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/40"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Table size={13} />
                <span>Data Preview</span>
                {previewData && (
                  <span
                    className="px-1.5 py-0.5 rounded-full text-[9px] font-mono border"
                    style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
                  >
                    {previewData.preview_count} rows
                  </span>
                )}
              </button>

              <button
                onClick={() => setViewingTab("sql")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-bold transition ${
                  viewingTab === "sql"
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/40"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <Code2 size={13} />
                <span>Generated SQL</span>
              </button>
            </div>

            {previewData && (
              <div className="flex items-center gap-3 text-[11px] font-mono text-zinc-400">
                <span>⏱ {previewData.execution_time_ms} ms</span>
                <span>·</span>
                <span>📊 {previewData.total_estimated_rows.toLocaleString()} est. total</span>
              </div>
            )}
          </div>

          {/* Results Area */}
          <div className="flex-1 min-h-0 overflow-auto">
            {viewingTab === "preview" ? (
              !previewData ? (
                <div className="h-full flex flex-col items-center justify-center p-8 text-center gap-3">
                  <div
                    className="w-12 h-12 rounded-2xl flex items-center justify-center border"
                    style={{ background: "rgba(99,102,241,0.1)", borderColor: "rgba(99,102,241,0.3)", color: "#818cf8" }}
                  >
                    <GitMerge size={22} />
                  </div>
                  <div className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                    Ready for In-Process Join Execution
                  </div>
                  <p className="text-xs max-w-sm" style={{ color: "var(--txt-m)" }}>
                    Click &ldquo;Run Preview&rdquo; to execute the join, rollups, and filters across DuckDB in memory.
                  </p>
                  <button
                    onClick={() => handlePreview()}
                    disabled={executingPreview}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold shadow-md cursor-pointer"
                    style={{ background: "var(--accent)", color: "#fff" }}
                  >
                    <Play size={12} />
                    <span>Run Preview</span>
                  </button>
                </div>
              ) : previewData.rows.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-zinc-400">
                  No rows returned by this query or filter condition.
                </div>
              ) : (
                <div className="w-full overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="sticky top-0 z-10 backdrop-blur border-b" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
                      <tr>
                        <th className="px-3 py-2 text-[10px] font-mono w-10" style={{ color: "var(--txt-m)" }}>#</th>
                        {previewData.columns.map((col, idx) => (
                          <th key={idx} className="px-3 py-2 font-mono whitespace-nowrap">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold" style={{ color: "var(--txt)" }}>{col.name}</span>
                              <span
                                className="px-1.5 py-0.5 rounded text-[8px] uppercase font-mono"
                                style={{ background: "var(--inp-bg)", color: "var(--txt-m)", border: "1px solid var(--border)" }}
                              >
                                {col.dtype}
                              </span>
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y font-mono text-[11px]" style={{ borderColor: "var(--border)" }}>
                      {previewData.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="transition" style={{ borderBottom: "1px solid var(--border)" }}>
                          <td className="px-3 py-1.5 select-none text-[10px]" style={{ color: "var(--txt-m)" }}>{rIdx + 1}</td>
                          {previewData.columns.map((col, cIdx) => (
                            <td key={cIdx} className="px-3 py-1.5 whitespace-nowrap" style={{ color: "var(--txt)" }}>
                              {row[col.name] !== null && row[col.name] !== undefined ? (
                                String(row[col.name])
                              ) : (
                                <span className="italic" style={{ color: "var(--txt-m)", opacity: 0.6 }}>null</span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            ) : (
              /* SQL VIEW */
              <div className="p-4 h-full flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono" style={{ color: "var(--txt-m)" }}>
                    In-Process Pushdown SQL (DuckDB v1.5 Engine)
                  </span>
                  <button
                    onClick={() => {
                      const textToCopy = previewData?.sql || customSql;
                      if (textToCopy) {
                        navigator.clipboard.writeText(textToCopy);
                        setCopiedSql(true);
                        setTimeout(() => setCopiedSql(false), 2000);
                      }
                    }}
                    className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition cursor-pointer"
                    style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                  >
                    <Copy size={12} />
                    <span>{copiedSql ? "Copied!" : "Copy SQL"}</span>
                  </button>
                </div>

                <pre
                  className="flex-1 p-4 rounded-xl border font-mono text-xs overflow-auto leading-relaxed select-all"
                  style={{
                    background: "var(--inp-bg)",
                    borderColor: "var(--border)",
                    color: "var(--txt)",
                  }}
                >
                  {previewData?.sql || customSql || "-- Click 'Run Preview' to generate pushdown SQL"}
                </pre>
              </div>
            )}

          </div>
        </div>
      </div>

      {/* -- UPLOAD SECONDARY TABLE MODAL ---- */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div
            className="w-full max-w-md p-6 rounded-3xl border shadow-2xl relative"
            style={{ background: "var(--card-bg, #121316)", borderColor: "var(--border)", color: "var(--txt)" }}
          >
            <button
              onClick={() => setShowUploadModal(false)}
              className="absolute top-5 right-5 p-1 rounded-full text-zinc-400 hover:text-zinc-200"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-2xl flex items-center justify-center"
                style={{ background: "rgba(255, 67, 16, 0.15)", color: "var(--accent)" }}
              >
                <Upload size={20} />
              </div>
              <div>
                <h3 className="text-base font-black">Add Secondary Table</h3>
                <p className="text-xs text-zinc-400">Upload CSV, Parquet, Excel, or JSON to join with your project.</p>
              </div>
            </div>

            <form onSubmit={handleUploadTable} className="space-y-4">
              <div>
                <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--txt)" }}>Table Identifier</label>
                <input
                  type="text"
                  placeholder="e.g. customers, inventory, clinical_visits"
                  value={uploadTableName}
                  onChange={(e) => setUploadTableName(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-xs border font-mono focus:outline-none"
                  style={{
                    background: "var(--inp-bg)",
                    borderColor: "var(--border)",
                    color: "var(--txt)",
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-bold mb-1.5" style={{ color: "var(--txt)" }}>File (.csv, .parquet, .json, .xlsx)</label>
                <input
                  type="file"
                  accept=".csv,.parquet,.json,.jsonl,.ndjson,.xlsx,.xls"
                  required
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      const ext = f.name.split(".").pop()?.toLowerCase();
                      const allowed = ["csv", "parquet", "json", "jsonl", "ndjson", "xlsx", "xls"];
                      if (!ext || !allowed.includes(ext)) {
                        showToast("error", `Unsupported file extension .${ext}. Supported: CSV, Parquet, JSON, Excel.`);
                        return;
                      }
                      setUploadFile(f);
                      if (!uploadTableName) {
                        setUploadTableName(f.name.replace(/\.[^/.]+$/, ""));
                      }
                    }
                  }}
                  className="w-full text-xs p-2 rounded-xl border cursor-pointer"
                  style={{
                    background: "var(--inp-bg)",
                    borderColor: "var(--border)",
                    color: "var(--txt)",
                  }}
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-bold border cursor-pointer"
                  style={{
                    background: "var(--card)",
                    borderColor: "var(--border)",
                    color: "var(--txt-m)",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !uploadFile}
                  className="px-5 py-2 rounded-xl text-xs font-bold shadow-lg transition hover:scale-[1.02] disabled:opacity-50 cursor-pointer"
                  style={{ background: "var(--accent)", color: "#fff" }}
                >
                  {isUploading ? "Uploading..." : "Register Table"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
