"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { apiFetch } from "@/lib/api";
import {
  FileSpreadsheet,
  Database,
  Plus,
  Trash2,
  Play,
  Sparkles,
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
  Filter,
  BarChart2,
  Terminal,
  Network,
  Search,
  Eye,
  ShieldAlert,
  ShieldCheck,
  ArrowDownUp,
  Link2,
  ExternalLink,
  Info,
} from "lucide-react";

// ── Types ───────────────────────────────────────────────────────────────────

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

interface SheetMeta {
  sheet_name: string;
  table_name: string;
  row_count: number;
  col_count: number;
  columns: string[];
  sample_preview?: any[][];
}

interface CompanionOriginResult {
  ok: boolean;
  has_companion_sheets: boolean;
  origin_type: string;
  url?: string;
  total_sheets?: number;
  imported_count?: number;
  unimported_sheets: SheetMeta[];
}

interface ReferentialAuditResult {
  ok: boolean;
  left_table: string;
  left_column: string;
  right_table: string;
  right_column: string;
  left_stats: {
    total_rows: number;
    distinct_keys: number;
    null_keys: number;
    is_unique: boolean;
  };
  right_stats: {
    total_rows: number;
    distinct_keys: number;
    null_keys: number;
    is_unique: boolean;
  };
  referential_metrics: {
    matched_keys_count: number;
    orphan_keys_count: number;
    orphan_rows_count: number;
    match_percentage: number;
    orphan_percentage: number;
    orphan_samples: string[];
    cardinality: string;
    fan_out_risk: "none" | "medium" | "high";
    health_score: number;
  };
  recommendations: string[];
  execution_time_ms: number;
}

interface DrillDownResult {
  ok: boolean;
  parent_table: string;
  child_table: string;
  parent_column: string;
  child_column: string;
  filter_value: string;
  total_matches: number;
  returned_count: number;
  columns: string[];
  records: any[];
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

export function MultiSheetTab() {
  const { uploadId, setProfile, setCleanProfile, setActiveTab, refreshWorkspace } = useWorkspace();

  // Studio View: "erd" | "visual" | "drilldown" | "sql"
  const [activeStudioView, setActiveStudioView] = useState<"erd" | "visual" | "drilldown" | "sql">("erd");

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

  // Toast / Status notification
  const [toast, setToast] = useState<{ type: "success" | "error" | "info"; msg: string } | null>(null);

  // Ingestion Modal State
  const [showIngestModal, setShowIngestModal] = useState<boolean>(false);
  const [ingestTab, setIngestTab] = useState<"companion" | "local" | "cloud">("local");
  const [companionOrigin, setCompanionOrigin] = useState<CompanionOriginResult | null>(null);
  const [inspectingOrigin, setInspectingOrigin] = useState<boolean>(false);

  // Local File Inspection State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isInspectingFile, setIsInspectingFile] = useState<boolean>(false);
  const [inspectedFileSheets, setInspectedFileSheets] = useState<SheetMeta[]>([]);
  const [selectedSheetsToImport, setSelectedSheetsToImport] = useState<Record<string, boolean>>({});
  const [customTableNames, setCustomTableNames] = useState<Record<string, string>>({});
  const [isImportingSheets, setIsImportingSheets] = useState<boolean>(false);

  // Cloud URL State
  const [cloudUrl, setCloudUrl] = useState<string>("");
  const [isInspectingCloud, setIsInspectingCloud] = useState<boolean>(false);
  const [cloudSheets, setCloudSheets] = useState<SheetMeta[]>([]);

  // Referential Audit Modal State
  const [showAuditModal, setShowAuditModal] = useState<boolean>(false);
  const [auditLeftTable, setAuditLeftTable] = useState<string>("");
  const [auditLeftCol, setAuditLeftCol] = useState<string>("");
  const [auditRightTable, setAuditRightTable] = useState<string>("");
  const [auditRightCol, setAuditRightCol] = useState<string>("");
  const [auditResult, setAuditResult] = useState<ReferentialAuditResult | null>(null);
  const [isRunningAudit, setIsRunningAudit] = useState<boolean>(false);

  // Interactive Drill-Down Explorer State
  const [drillParentTable, setDrillParentTable] = useState<string>("");
  const [drillChildTable, setDrillChildTable] = useState<string>("");
  const [drillParentCol, setDrillParentCol] = useState<string>("");
  const [drillChildCol, setDrillChildCol] = useState<string>("");
  const [drillSelectedParentRow, setDrillSelectedParentRow] = useState<any | null>(null);
  const [drillResult, setDrillResult] = useState<DrillDownResult | null>(null);
  const [isQueryingDrill, setIsQueryingDrill] = useState<boolean>(false);

  // ERD Search Filter
  const [erdSearch, setErdSearch] = useState<string>("");

  const showToast = (type: "success" | "error" | "info", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 4500);
  };

  // ── Fetch Workspace Tables & Relations ─────────────────────────────────────
  const fetchTables = useCallback(async () => {
    if (!uploadId) return;
    setLoadingTables(true);
    try {
      const res = await apiFetch(`/joins/tables?upload_id=${uploadId}`);
      if (res.ok) {
        const data = await res.json();
        setTables(data.tables || []);
        setRelationships(data.relationships || []);

        // Pick primary table or first table as baseTable if empty
        if (!baseTable && data.tables?.length > 0) {
          const prim = data.tables.find((t: TableSummary) => t.is_primary) || data.tables[0];
          setBaseTable(prim.name);
          setDrillParentTable(prim.name);
        }
      }
    } catch (e: any) {
      logError("Failed to fetch tables", e);
    } finally {
      setLoadingTables(false);
    }
  }, [uploadId, baseTable]);

  function logError(msg: string, e: any) {
    console.error(msg, e);
  }

  useEffect(() => {
    fetchTables();
  }, [fetchTables]);

  // Check Companion sheets origin on load
  const checkCompanionOrigin = useCallback(async () => {
    if (!uploadId) return;
    setInspectingOrigin(true);
    try {
      const res = await apiFetch(`/joins/sheets/workspace-origin?upload_id=${uploadId}`);
      if (res.ok) {
        const data: CompanionOriginResult = await res.json();
        setCompanionOrigin(data);
        if (data.has_companion_sheets && data.unimported_sheets?.length > 0) {
          // Initialize companion checklist
          const checked: Record<string, boolean> = {};
          const names: Record<string, string> = {};
          data.unimported_sheets.forEach((s) => {
            checked[s.sheet_name] = true;
            names[s.sheet_name] = s.table_name;
          });
          setSelectedSheetsToImport(checked);
          setCustomTableNames(names);
          setIngestTab("companion");
        }
      }
    } catch (e) {
      // quiet fail
    } finally {
      setInspectingOrigin(false);
    }
  }, [uploadId]);

  useEffect(() => {
    checkCompanionOrigin();
  }, [checkCompanionOrigin]);

  // Update Drill-Down defaults when tables load
  useEffect(() => {
    if (tables.length >= 2 && !drillChildTable) {
      const parent = tables.find((t) => t.name === (drillParentTable || baseTable)) || tables[0];
      const child = tables.find((t) => t.name !== parent.name) || tables[1];
      setDrillParentTable(parent.name);
      setDrillChildTable(child.name);

      // Check if there is an inferred relationship between them
      const rel = relationships.find(
        (r) =>
          (r.left_table === parent.name && r.right_table === child.name) ||
          (r.left_table === child.name && r.right_table === parent.name)
      );
      if (rel) {
        if (rel.left_table === parent.name) {
          setDrillParentCol(rel.left_column);
          setDrillChildCol(rel.right_column);
        } else {
          setDrillParentCol(rel.right_column);
          setDrillChildCol(rel.left_column);
        }
      } else {
        if (parent.columns[0]) setDrillParentCol(parent.columns[0].name);
        if (child.columns[0]) setDrillChildCol(child.columns[0].name);
      }
    }
  }, [tables, relationships, drillParentTable, drillChildTable, baseTable]);

  // ── Preset Schemas ────────────────────────────────────────────────────────
  const handleLoadPreset = async (preset: "ecommerce" | "saas" | "healthcare") => {
    if (!uploadId) return;
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
          setBaseTable("orders");
          setJoins([
            {
              table: "customers",
              join_type: "LEFT",
              conditions: [{ left_col: "customer_id", right_col: "customer_id", left_table: "orders" }],
            },
            {
              table: "products",
              join_type: "LEFT",
              conditions: [{ left_col: "order_id", right_col: "product_id", left_table: "orders" }],
              rollup: {
                table: "products",
                group_by: ["category"],
                aggregates: [
                  { column: "unit_price", function: "AVG", alias: "avg_category_price" },
                  { column: "product_id", function: "COUNT", alias: "category_product_count" },
                ],
              },
            },
          ]);
          setFilters([
            { table: "customers", column: "loyalty_tier", operator: "IN", value: "Gold, Platinum" },
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
          setFilters([{ table: "patients", column: "age", operator: ">=", value: "45" }]);
          setCustomSql(
            `SELECT p.patient_id, p.age, p.gender, AVG(v.systolic_bp) as avg_bp, AVG(v.glucose_mg_dl) as avg_glucose\nFROM patients p\nJOIN clinical_visits v ON p.patient_id = v.patient_id\nWHERE p.age >= 45\nGROUP BY p.patient_id, p.age, p.gender\nORDER BY avg_glucose DESC;`
          );
        }

        showToast("success", `Relational schema loaded: ${data.message}`);
        setTimeout(() => handlePreview(true), 250);
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

  // ── Inspect Local File on Drop / Pick ──────────────────────────────────────
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);

    const ext = file.name.split(".").pop()?.toLowerCase() || "";
    if (ext === "xlsx" || ext === "xls") {
      setIsInspectingFile(true);
      const fd = new FormData();
      fd.append("file", file);
      try {
        const res = await apiFetch("/joins/sheets/inspect-file", {
          method: "POST",
          body: fd,
        });
        if (res.ok) {
          const data = await res.json();
          const sheets: SheetMeta[] = data.sheets || [];
          setInspectedFileSheets(sheets);
          const checked: Record<string, boolean> = {};
          const names: Record<string, string> = {};
          sheets.forEach((s) => {
            checked[s.sheet_name] = true;
            names[s.sheet_name] = s.table_name;
          });
          setSelectedSheetsToImport(checked);
          setCustomTableNames(names);
        } else {
          showToast("error", "Could not inspect Excel workbook.");
        }
      } catch (err: any) {
        showToast("error", err.message || "File inspection error.");
      } finally {
        setIsInspectingFile(false);
      }
    } else {
      // Non-Excel files (CSV, Parquet, JSON)
      const baseClean = file.name.replace(/\.[^/.]+$/, "").replace(/[^\w]/g, "_").toLowerCase();
      setInspectedFileSheets([
        {
          sheet_name: file.name,
          table_name: baseClean,
          row_count: -1,
          col_count: -1,
          columns: [],
        },
      ]);
      setSelectedSheetsToImport({ [file.name]: true });
      setCustomTableNames({ [file.name]: baseClean });
    }
  };

  // ── Inspect Cloud Sheet URL ───────────────────────────────────────────────
  const handleInspectCloud = async () => {
    if (!cloudUrl.trim()) return;
    setIsInspectingCloud(true);
    try {
      const res = await apiFetch("/joins/sheets/inspect-url", {
        method: "POST",
        body: JSON.stringify({
          source_type: cloudUrl.includes("docs.google.com") ? "google_sheets" : "excel_online",
          url: cloudUrl.trim(),
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const sheets: SheetMeta[] = data.sheets || [];
        setCloudSheets(sheets);
        const checked: Record<string, boolean> = {};
        const names: Record<string, string> = {};
        sheets.forEach((s) => {
          checked[s.sheet_name] = true;
          names[s.sheet_name] = s.table_name;
        });
        setSelectedSheetsToImport(checked);
        setCustomTableNames(names);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Failed to inspect cloud spreadsheet.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Network error inspecting sheet.");
    } finally {
      setIsInspectingCloud(false);
    }
  };

  // ── Import Selected Sheets into Workspace ─────────────────────────────────
  const handleExecuteImport = async () => {
    if (!uploadId) return;
    setIsImportingSheets(true);

    const sheetsToImport = Object.entries(selectedSheetsToImport)
      .filter(([_, isChecked]) => isChecked)
      .map(([sName]) => ({
        sheet_name: sName,
        table_name: customTableNames[sName] || sName,
      }));

    if (sheetsToImport.length === 0) {
      showToast("info", "Please select at least one worksheet to import.");
      setIsImportingSheets(false);
      return;
    }

    try {
      if (ingestTab === "local" && selectedFile) {
        const ext = selectedFile.name.split(".").pop()?.toLowerCase();
        if (ext === "xlsx" || ext === "xls") {
          // Upload file for extraction
          const fd = new FormData();
          fd.append("upload_id", uploadId);
          fd.append("file", selectedFile);
          // For Excel with multiple sheets, we can upload each selected sheet or use /joins/tables/upload
          for (const item of sheetsToImport) {
            const formData = new FormData();
            formData.append("upload_id", uploadId);
            formData.append("file", selectedFile);
            formData.append("table_name", item.table_name);
            await apiFetch("/joins/tables/upload", { method: "POST", body: formData });
          }
        } else {
          const formData = new FormData();
          formData.append("upload_id", uploadId);
          formData.append("file", selectedFile);
          formData.append("table_name", sheetsToImport[0].table_name);
          await apiFetch("/joins/tables/upload", { method: "POST", body: formData });
        }
      } else if (ingestTab === "companion") {
        const res = await apiFetch("/joins/sheets/import", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            source_type: companionOrigin?.origin_type || "excel_local",
            source_url: companionOrigin?.url,
            selected_sheets: sheetsToImport,
          }),
        });
        if (!res.ok) throw new Error("Failed importing companion sheets.");
      } else if (ingestTab === "cloud") {
        const res = await apiFetch("/joins/sheets/import", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            source_type: cloudUrl.includes("docs.google.com") ? "google_sheets" : "excel_online",
            source_url: cloudUrl.trim(),
            selected_sheets: sheetsToImport,
          }),
        });
        if (!res.ok) throw new Error("Failed importing cloud sheets.");
      }

      await fetchTables();
      await checkCompanionOrigin();
      setShowIngestModal(false);
      showToast("success", `Imported ${sheetsToImport.length} table(s) into workspace.`);
    } catch (e: any) {
      showToast("error", e.message || "Failed to import selected sheets.");
    } finally {
      setIsImportingSheets(false);
    }
  };

  // ── Delete Table ──────────────────────────────────────────────────────────
  const handleDeleteTable = async (tableName: string) => {
    if (!uploadId) return;
    try {
      const res = await apiFetch(`/joins/tables/${tableName}?upload_id=${uploadId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast("info", `Table '${tableName}' removed from workspace.`);
        await fetchTables();
        await checkCompanionOrigin();
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Cannot delete primary table.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Delete error.");
    }
  };

  // ── Referential Integrity Audit ───────────────────────────────────────────
  const runIntegrityAudit = async (leftT: string, leftC: string, rightT: string, rightC: string) => {
    if (!uploadId || !leftT || !leftC || !rightT || !rightC) return;
    setIsRunningAudit(true);
    setAuditLeftTable(leftT);
    setAuditLeftCol(leftC);
    setAuditRightTable(rightT);
    setAuditRightCol(rightC);
    setShowAuditModal(true);

    try {
      const res = await apiFetch("/joins/analytics/integrity-audit", {
        method: "POST",
        body: JSON.stringify({
          upload_id: uploadId,
          left_table: leftT,
          left_column: leftC,
          right_table: rightT,
          right_column: rightC,
        }),
      });
      if (res.ok) {
        const data: ReferentialAuditResult = await res.json();
        setAuditResult(data);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Referential audit failed.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Audit error.");
    } finally {
      setIsRunningAudit(false);
    }
  };

  // ── Interactive Drill-Down Query ──────────────────────────────────────────
  const handleQueryDrillDown = async (parentRow: any) => {
    if (!uploadId || !drillParentTable || !drillChildTable || !drillParentCol || !drillChildCol) return;
    setDrillSelectedParentRow(parentRow);
    const parentVal = parentRow[drillParentCol];
    if (parentVal === undefined || parentVal === null) return;

    setIsQueryingDrill(true);
    try {
      const res = await apiFetch("/joins/analytics/drill-down", {
        method: "POST",
        body: JSON.stringify({
          upload_id: uploadId,
          parent_table: drillParentTable,
          child_table: drillChildTable,
          parent_column: drillParentCol,
          child_column: drillChildCol,
          parent_value: parentVal,
          limit: 100,
        }),
      });
      if (res.ok) {
        const data: DrillDownResult = await res.json();
        setDrillResult(data);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Drill-down query failed.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Drill-down error.");
    } finally {
      setIsQueryingDrill(false);
    }
  };

  // ── Join Pipeline Helpers ─────────────────────────────────────────────────
  const addJoinStep = (targetTable: string) => {
    const target = tables.find((t) => t.name === targetTable);
    if (!target) return;

    const base = tables.find((t) => t.name === baseTable);
    let leftCol = base?.columns[0]?.name || "";
    let rightCol = target.columns[0]?.name || "";

    const candidate = relationships.find(
      (r) =>
        (r.left_table === baseTable && r.right_table === targetTable) ||
        (r.right_table === baseTable && r.left_table === targetTable)
    );

    if (candidate) {
      if (candidate.left_table === baseTable) {
        leftCol = candidate.left_column;
        rightCol = candidate.right_column;
      } else {
        leftCol = candidate.right_column;
        rightCol = candidate.left_column;
      }
    }

    setJoins([
      ...joins,
      {
        table: targetTable,
        join_type: "LEFT",
        conditions: [{ left_col: leftCol, right_col: rightCol, left_table: baseTable }],
      },
    ]);
  };

  const removeJoinStep = (index: number) => {
    setJoins(joins.filter((_, idx) => idx !== index));
    if (expandedRollupIdx === index) setExpandedRollupIdx(null);
  };

  const updateJoinType = (index: number, join_type: JoinDefinition["join_type"]) => {
    const updated = [...joins];
    updated[index].join_type = join_type;
    setJoins(updated);
  };

  const updateCondition = (
    jIdx: number,
    cIdx: number,
    field: "left_col" | "right_col" | "left_table",
    val: string
  ) => {
    const updated = [...joins];
    updated[jIdx].conditions[cIdx] = {
      ...updated[jIdx].conditions[cIdx],
      [field]: val,
    };
    setJoins(updated);
  };

  const toggleRollup = (index: number) => {
    const updated = [...joins];
    const j = updated[index];
    if (j.rollup) {
      delete j.rollup;
      setExpandedRollupIdx(null);
    } else {
      const targetObj = tables.find((t) => t.name === j.table);
      const condKey = j.conditions[0]?.right_col || targetObj?.columns[0]?.name || "";
      const numCol = targetObj?.columns.find(
        (c) => c.dtype.toLowerCase().includes("int") || c.dtype.toLowerCase().includes("float")
      )?.name || condKey;

      j.rollup = {
        table: j.table,
        group_by: [condKey],
        aggregates: [
          {
            column: numCol,
            function: "SUM",
            alias: `total_${numCol}`,
          },
        ],
      };
      setExpandedRollupIdx(index);
    }
    setJoins(updated);
  };

  const addFilter = () => {
    if (tables.length === 0) return;
    const t = tables[0];
    setFilters([
      ...filters,
      {
        table: t.name,
        column: t.columns[0]?.name || "",
        operator: "=",
        value: "",
      },
    ]);
  };

  const removeFilter = (index: number) => {
    setFilters(filters.filter((_, idx) => idx !== index));
  };

  // ── Preview & Materialize ─────────────────────────────────────────────────
  const handlePreview = async (silent: boolean = false) => {
    if (!uploadId) return;
    setExecutingPreview(true);

    try {
      let res;
      if (activeStudioView === "sql" && customSql.trim()) {
        res = await apiFetch("/joins/sql/preview", {
          method: "POST",
          body: JSON.stringify({ upload_id: uploadId, sql: customSql, limit: 50 }),
        });
      } else {
        res = await apiFetch("/joins/preview", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            base_table: baseTable,
            joins: joins,
            filters: filters,
            limit: 50,
          }),
        });
      }

      if (res.ok) {
        const data = await res.json();
        setPreviewData(data);
        if (!silent) showToast("success", `DuckDB executed in ${data.execution_time_ms} ms (${data.preview_count} rows).`);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "DuckDB query error.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Execution error.");
    } finally {
      setExecutingPreview(false);
    }
  };

  const handleMaterialize = async () => {
    if (!uploadId) return;
    setMaterializing(true);

    try {
      let res;
      if (activeStudioView === "sql" && customSql.trim()) {
        res = await apiFetch("/joins/sql/materialize", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            sql: customSql,
            output_dataset_name: "custom_sql_dataset.csv",
          }),
        });
      } else {
        res = await apiFetch("/joins/materialize", {
          method: "POST",
          body: JSON.stringify({
            upload_id: uploadId,
            base_table: baseTable,
            joins: joins,
            filters: filters,
            output_dataset_name: `joined_${baseTable}_dataset.csv`,
          }),
        });
      }

      if (res.ok) {
        const data = await res.json();
        if (data.profile) {
          setProfile(data.profile);
          setCleanProfile(data.profile);
        }
        await refreshWorkspace();
        showToast("success", `Dataset materialized! ${data.rows?.toLocaleString()} rows committed to active workspace.`);
        setTimeout(() => setActiveTab("preview"), 600);
      } else {
        const err = await res.json().catch(() => ({}));
        showToast("error", err.detail || "Materialization failed.");
      }
    } catch (e: any) {
      showToast("error", e.message || "Materialization error.");
    } finally {
      setMaterializing(false);
    }
  };

  // ── Filtered Tables for ERD ───────────────────────────────────────────────
  const filteredErdTables = useMemo(() => {
    if (!erdSearch.trim()) return tables;
    const q = erdSearch.toLowerCase();
    return tables.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.columns.some((c) => c.name.toLowerCase().includes(q))
    );
  }, [tables, erdSearch]);

  // Overall Health Score average
  const schemaHealthScore = useMemo(() => {
    if (relationships.length === 0) return 100;
    const avgConfidence = relationships.reduce((acc, r) => acc + r.confidence, 0) / relationships.length;
    return Math.round(avgConfidence * 100);
  }, [relationships]);

  // Available secondary tables for join picker
  const availableSecondaryTables = useMemo(() => {
    return tables.filter((t) => t.name !== baseTable && !joins.some((j) => j.table === t.name));
  }, [tables, baseTable, joins]);

  return (
    <div className="flex flex-col h-full w-full overflow-hidden" style={{ background: "var(--surface)", color: "var(--txt)" }}>
      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold shadow-xl border transition-all ${
            toast.type === "success"
              ? "bg-emerald-950/90 border-emerald-800 text-emerald-200"
              : toast.type === "error"
              ? "bg-rose-950/90 border-rose-800 text-rose-200"
              : "bg-zinc-900 border-zinc-700 text-zinc-200"
          }`}
        >
          {toast.type === "success" && <Check size={14} className="text-emerald-400" />}
          {toast.type === "error" && <AlertCircle size={14} className="text-rose-400" />}
          {toast.type === "info" && <Info size={14} className="text-blue-400" />}
          <span>{toast.msg}</span>
        </div>
      )}

      {/* ── Top Bar & Segmented Mode Switcher ──────────────────────────────── */}
      <div
        className="flex items-center justify-between px-6 py-3 border-b shrink-0"
        style={{ borderColor: "var(--border)", background: "var(--card)" }}
      >
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg border border-[var(--border)]" style={{ background: "var(--surface)" }}>
            <FileSpreadsheet size={18} style={{ color: "var(--accent)" }} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight">Multi-Sheet Studio</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-[var(--border)]" style={{ color: "var(--txt-m)" }}>
                {tables.length} table{tables.length === 1 ? "" : "s"} ({tables.reduce((acc, t) => acc + t.row_count, 0).toLocaleString()} total rows)
              </span>
            </div>
            <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
              Multi-table schema modeling, referential integrity audit, cross-sheet drill-downs & DuckDB joins
            </p>
          </div>
        </div>

        {/* Studio View Selector */}
        <div className="flex items-center gap-2">
          <div
            className="flex items-center p-1 rounded-xl border"
            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
          >
            {[
              { id: "erd", label: "Schema ERD", icon: Network },
              { id: "visual", label: "Visual Join", icon: Layers },
              { id: "drilldown", label: "Drill-Down", icon: Eye },
              { id: "sql", label: "DuckDB SQL", icon: Terminal },
            ].map((v) => {
              const Icon = v.icon;
              const isActive = activeStudioView === v.id;
              return (
                <button
                  key={v.id}
                  onClick={() => setActiveStudioView(v.id as any)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
                    isActive
                      ? "bg-[var(--card)] text-[var(--txt)] shadow-xs border border-[var(--border)]"
                      : "text-[var(--txt-m)] hover:text-[var(--txt)]"
                  }`}
                >
                  <Icon size={13} style={{ color: isActive ? "var(--accent)" : "currentColor" }} />
                  <span>{v.label}</span>
                </button>
              );
            })}
          </div>

          {/* Add Sheet / Table Button */}
          <button
            onClick={() => setShowIngestModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition hover:opacity-90 cursor-pointer"
            style={{ background: "var(--accent)", color: "#fff" }}
          >
            <Plus size={13} />
            <span>Add Sheet / Table</span>
          </button>
        </div>
      </div>

      {/* ── Main Studio Body ──────────────────────────────────────────────── */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {/* VIEW 1: SCHEMA ERD MATRIX */}
        {activeStudioView === "erd" && (
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
            {/* Health & Search Bar */}
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[var(--border)]" style={{ background: "var(--card)" }}>
                  <ShieldCheck size={14} className="text-emerald-500" />
                  <span className="text-xs font-bold">Schema Health:</span>
                  <span className="text-xs font-mono font-bold text-emerald-500">{schemaHealthScore}%</span>
                </div>
                {companionOrigin?.has_companion_sheets && companionOrigin.unimported_sheets.length > 0 && (
                  <button
                    onClick={() => {
                      setIngestTab("companion");
                      setShowIngestModal(true);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300 hover:bg-amber-500/20 transition cursor-pointer"
                  >
                    <AlertCircle size={13} />
                    <span>{companionOrigin.unimported_sheets.length} Unimported Sheet(s) Found</span>
                  </button>
                )}
              </div>

              {/* Search Columns/Tables */}
              <div className="relative w-64">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--txt-m)]" />
                <input
                  type="text"
                  placeholder="Filter tables or columns..."
                  value={erdSearch}
                  onChange={(e) => setErdSearch(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 text-xs rounded-xl border border-[var(--border)] bg-[var(--card)] text-[var(--txt)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                />
              </div>
            </div>

            {/* Inferred Relationships Summary Strip */}
            {relationships.length > 0 && (
              <div className="flex flex-col gap-2 p-4 rounded-2xl border" style={{ borderColor: "var(--border)", background: "var(--card)" }}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold tracking-tight">Discovered Foreign Key Links ({relationships.length})</span>
                  <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>Click any connection to audit referential integrity</span>
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {relationships.map((r, rIdx) => (
                    <button
                      key={rIdx}
                      onClick={() => runIntegrityAudit(r.left_table, r.left_column, r.right_table, r.right_column)}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] transition text-xs group cursor-pointer"
                      style={{ background: "var(--surface)" }}
                    >
                      <span className="font-semibold">{r.left_table}.{r.left_column}</span>
                      <ArrowRight size={11} className="text-zinc-500 group-hover:text-[var(--accent)]" />
                      <span className="font-semibold">{r.right_table}.{r.right_column}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-zinc-800 text-zinc-300">
                        {r.cardinality}
                      </span>
                      <span className="text-[10px] font-mono text-emerald-400 font-bold">
                        {Math.round(r.confidence * 100)}%
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Entity Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredErdTables.map((t) => (
                <div
                  key={t.name}
                  className="flex flex-col rounded-2xl border transition shadow-xs"
                  style={{ borderColor: "var(--border)", background: "var(--card)" }}
                >
                  {/* Entity Header */}
                  <div className="flex items-center justify-between p-3.5 border-b border-[var(--border)]">
                    <div className="flex items-center gap-2">
                      <Table size={14} style={{ color: t.is_primary ? "var(--accent)" : "var(--txt-m)" }} />
                      <span className="text-xs font-bold tracking-tight">{t.name}</span>
                      {t.is_primary && (
                        <span className="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded bg-[var(--accent)] text-white">
                          Base
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {!t.is_primary && (
                        <button
                          onClick={() => handleDeleteTable(t.name)}
                          className="p-1 rounded text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                          title="Remove table"
                        >
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Entity Stats */}
                  <div className="flex items-center justify-between px-3.5 py-2 text-[10px] border-b border-[var(--border)]" style={{ color: "var(--txt-m)" }}>
                    <span>{t.row_count.toLocaleString()} rows</span>
                    <span>{t.columns.length} columns</span>
                  </div>

                  {/* Columns List */}
                  <div className="flex-1 p-2 flex flex-col gap-1 max-h-64 overflow-y-auto">
                    {t.columns.map((c) => {
                      const isKey = relationships.some(
                        (r) =>
                          (r.left_table === t.name && r.left_column === c.name) ||
                          (r.right_table === t.name && r.right_column === c.name)
                      );
                      return (
                        <div
                          key={c.name}
                          className="flex items-center justify-between px-2 py-1 rounded text-[11px] hover:bg-[var(--surface)] transition"
                        >
                          <div className="flex items-center gap-1.5 truncate">
                            {isKey ? (
                              <Link2 size={11} className="text-emerald-500 shrink-0" />
                            ) : (
                              <span className="w-2.5 shrink-0" />
                            )}
                            <span className="font-medium truncate">{c.name}</span>
                          </div>
                          <span className="text-[9px] font-mono shrink-0" style={{ color: "var(--txt-m)" }}>
                            {c.dtype}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Entity Footer Action */}
                  <div className="p-2 border-t border-[var(--border)] flex items-center justify-between">
                    <button
                      onClick={() => {
                        setDrillParentTable(t.name);
                        setActiveStudioView("drilldown");
                      }}
                      className="text-[10px] font-bold text-[var(--accent)] hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      <span>Inspect & Drill Down</span>
                      <ArrowRight size={10} />
                    </button>
                    {!t.is_primary && (
                      <button
                        onClick={() => addJoinStep(t.name)}
                        className="text-[10px] font-bold text-zinc-400 hover:text-[var(--txt)] flex items-center gap-1 cursor-pointer"
                      >
                        <span>+ Join</span>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* VIEW 2: VISUAL JOIN CANVAS */}
        {activeStudioView === "visual" && (
          <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Join Pipeline Steps */}
              <div className="lg:col-span-2 flex flex-col gap-4">
                {/* Base Table Selector */}
                <div
                  className="p-4 rounded-2xl border flex items-center justify-between"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold">Base Table (FROM):</span>
                    <select
                      value={baseTable}
                      onChange={(e) => setBaseTable(e.target.value)}
                      className="border rounded-lg px-2.5 py-1 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                      style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                    >
                      {tables.map((t) => (
                        <option key={t.name} value={t.name}>
                          {t.name} ({t.row_count.toLocaleString()} rows)
                        </option>
                      ))}
                    </select>
                  </div>

                  {availableSecondaryTables.length > 0 && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px]" style={{ color: "var(--txt-m)" }}>Add Table:</span>
                      {availableSecondaryTables.map((t) => (
                        <button
                          key={t.name}
                          onClick={() => addJoinStep(t.name)}
                          className="px-2 py-1 rounded-lg text-[10px] font-bold border border-[var(--border)] hover:border-[var(--accent)] transition cursor-pointer"
                        >
                          + {t.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Joins List */}
                {joins.length === 0 ? (
                  <div
                    className="p-8 rounded-2xl border border-dashed flex flex-col items-center justify-center gap-3 text-center"
                    style={{ borderColor: "var(--border)", background: "var(--card)" }}
                  >
                    <Layers size={28} className="text-[var(--txt-m)]" />
                    <div className="text-xs font-bold">No Joins Configured Yet</div>
                    <p className="text-[11px] max-w-sm" style={{ color: "var(--txt-m)" }}>
                      Combine {baseTable || "the base table"} with another dataset using Left, Inner, Right, or Full Outer joins.
                    </p>
                    {availableSecondaryTables.length > 0 && (
                      <button
                        onClick={() => addJoinStep(availableSecondaryTables[0].name)}
                        className="px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer"
                        style={{ background: "var(--accent)", color: "#fff" }}
                      >
                        Join with {availableSecondaryTables[0].name}
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
                        className="p-4 rounded-2xl border flex flex-col gap-3"
                        style={{ background: "var(--card)", borderColor: "var(--border)" }}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold border border-[var(--border)]">
                              Step {idx + 1}
                            </span>
                            <div className="flex items-center gap-1.5 text-xs font-bold">
                              <span>{j.conditions[0]?.left_table || baseTable}</span>
                              <ArrowRight size={12} className="text-zinc-500" />
                              <span style={{ color: "var(--accent)" }}>{j.table}</span>
                              {j.rollup && (
                                <span className="px-1.5 py-0.2 rounded text-[8px] font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                                  Rollup Active
                                </span>
                              )}
                            </div>
                          </div>

                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => toggleRollup(idx)}
                              className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-bold border transition ${
                                j.rollup
                                  ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                                  : "border-[var(--border)] text-[var(--txt-m)] hover:text-[var(--txt)]"
                              }`}
                            >
                              <BarChart2 size={11} />
                              <span>{j.rollup ? "Rollup Active" : "+ Pre-Join Rollup"}</span>
                            </button>
                            <button
                              onClick={() => removeJoinStep(idx)}
                              className="p-1 rounded-lg hover:bg-rose-500/10 text-zinc-400 hover:text-rose-400 transition"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>

                        {/* Join Type & Conditions */}
                        <div className="flex items-center gap-3 text-xs">
                          <select
                            value={j.join_type}
                            onChange={(e) => updateJoinType(idx, e.target.value as any)}
                            className="border rounded-lg px-2.5 py-1 text-xs font-semibold focus:outline-none"
                            style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                          >
                            {JOIN_TYPES.map((t) => (
                              <option key={t.id} value={t.id}>
                                {t.label} ({t.symbol})
                              </option>
                            ))}
                          </select>

                          {j.conditions.map((cond, cIdx) => (
                            <div key={cIdx} className="flex items-center gap-2">
                              <select
                                value={cond.left_col}
                                onChange={(e) => updateCondition(idx, cIdx, "left_col", e.target.value)}
                                className="border rounded-lg px-2 py-1 text-xs focus:outline-none"
                                style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                              >
                                {baseObj?.columns.map((c) => (
                                  <option key={c.name} value={c.name}>
                                    {c.name}
                                  </option>
                                ))}
                              </select>
                              <span className="text-xs font-bold text-zinc-400">=</span>
                              <select
                                value={cond.right_col}
                                onChange={(e) => updateCondition(idx, cIdx, "right_col", e.target.value)}
                                className="border rounded-lg px-2 py-1 text-xs focus:outline-none"
                                style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                              >
                                {targetObj?.columns.map((c) => (
                                  <option key={c.name} value={c.name}>
                                    {c.name}
                                  </option>
                                ))}
                              </select>

                              {/* Quick Audit Button */}
                              <button
                                onClick={() =>
                                  runIntegrityAudit(
                                    cond.left_table || baseTable,
                                    cond.left_col,
                                    j.table,
                                    cond.right_col
                                  )
                                }
                                className="p-1 rounded text-zinc-400 hover:text-[var(--accent)] hover:bg-zinc-800 transition"
                                title="Audit foreign key referential integrity"
                              >
                                <ShieldCheck size={13} />
                              </button>
                            </div>
                          ))}
                        </div>

                        {/* Pre-Join Rollup Details if open */}
                        {isRollupOpen && j.rollup && (
                          <div
                            className="p-3 rounded-xl border flex flex-col gap-2 mt-1"
                            style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                          >
                            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                              Pre-Join Rollup (CTE Pre-Aggregation to prevent row duplication)
                            </span>
                            <div className="flex items-center gap-2 text-xs">
                              <span>Group By:</span>
                              <span className="font-mono text-emerald-400">{j.rollup.group_by.join(", ")}</span>
                              <span className="ml-2">Aggregate:</span>
                              <span className="font-mono">{j.rollup.aggregates[0]?.function}({j.rollup.aggregates[0]?.column}) AS {j.rollup.aggregates[0]?.alias}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}

                {/* Where Filters Strip */}
                <div
                  className="p-4 rounded-2xl border flex flex-col gap-3"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold">Query Filters (WHERE)</span>
                    <button
                      onClick={addFilter}
                      className="text-[11px] font-bold text-[var(--accent)] hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      <Plus size={11} />
                      <span>Add Filter</span>
                    </button>
                  </div>
                  {filters.length === 0 ? (
                    <span className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                      No filters applied. Entire dataset will be joined.
                    </span>
                  ) : (
                    filters.map((f, fIdx) => (
                      <div key={fIdx} className="flex items-center gap-2 text-xs">
                        <select
                          value={f.table}
                          onChange={(e) => {
                            const updated = [...filters];
                            updated[fIdx].table = e.target.value;
                            setFilters(updated);
                          }}
                          className="border rounded-lg px-2 py-1 text-xs"
                          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                        >
                          {tables.map((t) => (
                            <option key={t.name} value={t.name}>
                              {t.name}
                            </option>
                          ))}
                        </select>
                        <select
                          value={f.column}
                          onChange={(e) => {
                            const updated = [...filters];
                            updated[fIdx].column = e.target.value;
                            setFilters(updated);
                          }}
                          className="border rounded-lg px-2 py-1 text-xs"
                          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                        >
                          {tables.find((t) => t.name === f.table)?.columns.map((c) => (
                            <option key={c.name} value={c.name}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                        <select
                          value={f.operator}
                          onChange={(e) => {
                            const updated = [...filters];
                            updated[fIdx].operator = e.target.value as any;
                            setFilters(updated);
                          }}
                          className="border rounded-lg px-2 py-1 text-xs"
                          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                        >
                          {FILTER_OPERATORS.map((op) => (
                            <option key={op.id} value={op.id}>
                              {op.label}
                            </option>
                          ))}
                        </select>
                        <input
                          type="text"
                          placeholder="Value..."
                          value={f.value}
                          onChange={(e) => {
                            const updated = [...filters];
                            updated[fIdx].value = e.target.value;
                            setFilters(updated);
                          }}
                          className="border rounded-lg px-2.5 py-1 text-xs w-36"
                          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                        />
                        <button
                          onClick={() => removeFilter(fIdx)}
                          className="p-1 rounded text-zinc-400 hover:text-rose-400"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Right Column: Execution Controls & Relational Presets */}
              <div className="flex flex-col gap-4">
                <div
                  className="p-4 rounded-2xl border flex flex-col gap-3"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <span className="text-xs font-bold tracking-tight">DuckDB Pushdown Execution</span>
                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => handlePreview(false)}
                      disabled={executingPreview}
                      className="w-full py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition hover:opacity-95 cursor-pointer"
                      style={{ background: "var(--accent)", color: "#fff" }}
                    >
                      {executingPreview ? <RefreshCw size={13} className="animate-spin" /> : <Play size={13} />}
                      <span>{executingPreview ? "Running DuckDB..." : "Preview Pushdown Join"}</span>
                    </button>

                    <button
                      onClick={handleMaterialize}
                      disabled={materializing || !previewData}
                      className="w-full py-2.5 rounded-xl text-xs font-bold border flex items-center justify-center gap-2 transition hover:bg-emerald-500/10 cursor-pointer disabled:opacity-40"
                      style={{ borderColor: "var(--border)" }}
                    >
                      {materializing ? <RefreshCw size={13} className="animate-spin" /> : <Check size={13} />}
                      <span>{materializing ? "Materializing Parquet..." : "Materialize to Workspace"}</span>
                    </button>
                  </div>
                </div>

                {/* 1-Click Relational Schema Presets */}
                <div
                  className="p-4 rounded-2xl border flex flex-col gap-2.5"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <span className="text-xs font-bold tracking-tight">Load Relational Schema Preset</span>
                  <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                    Instantly load a normalized multi-table database schema with primary and foreign keys.
                  </p>
                  <div className="flex flex-col gap-1.5 pt-1">
                    {[
                      { id: "ecommerce", label: "E-Commerce", desc: "Customers + Orders + Products" },
                      { id: "saas", label: "SaaS Analytics", desc: "Organizations + Subscriptions" },
                      { id: "healthcare", label: "Healthcare", desc: "Patients + Clinical Visits" },
                    ].map((p) => (
                      <button
                        key={p.id}
                        onClick={() => handleLoadPreset(p.id as any)}
                        disabled={Boolean(loadingPreset)}
                        className="flex items-center justify-between p-2 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] transition text-xs text-left cursor-pointer"
                        style={{ background: "var(--surface)" }}
                      >
                        <div>
                          <div className="font-bold">{p.label}</div>
                          <div className="text-[10px]" style={{ color: "var(--txt-m)" }}>{p.desc}</div>
                        </div>
                        {loadingPreset === p.id ? (
                          <RefreshCw size={12} className="animate-spin" />
                        ) : (
                          <ArrowRight size={12} className="text-zinc-500" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Preview Results Table */}
            {previewData && (
              <div
                className="p-4 rounded-2xl border flex flex-col gap-3"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold">DuckDB Pushdown Results</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-[var(--border)]">
                      {previewData.preview_count} rows in {previewData.execution_time_ms} ms
                    </span>
                  </div>
                </div>

                <div className="overflow-x-auto max-h-72 border rounded-xl border-[var(--border)]">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="sticky top-0 bg-[var(--surface)] border-b border-[var(--border)]">
                      <tr>
                        {previewData.columns.map((c) => (
                          <th key={c.name} className="px-3 py-2 font-bold whitespace-nowrap">
                            <div>{c.name}</div>
                            <div className="text-[9px] font-mono font-normal" style={{ color: "var(--txt-m)" }}>
                              {c.dtype}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.rows.map((r, rIdx) => (
                        <tr key={rIdx} className="border-b border-[var(--border)] hover:bg-[var(--surface)] transition">
                          {previewData.columns.map((c) => (
                            <td key={c.name} className="px-3 py-1.5 font-mono whitespace-nowrap">
                              {r[c.name] !== null && r[c.name] !== undefined ? String(r[c.name]) : "NULL"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* VIEW 3: CROSS-SHEET DRILL-DOWN EXPLORER */}
        {activeStudioView === "drilldown" && (
          <div className="flex-1 overflow-hidden p-6 flex flex-col gap-4">
            {/* Header controls for Drill Down */}
            <div
              className="p-4 rounded-2xl border flex flex-wrap items-center justify-between gap-4"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex flex-wrap items-center gap-3 text-xs">
                <span className="font-bold">Master Table:</span>
                <select
                  value={drillParentTable}
                  onChange={(e) => setDrillParentTable(e.target.value)}
                  className="border rounded-lg px-2.5 py-1 font-semibold"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  {tables.map((t) => (
                    <option key={t.name} value={t.name}>
                      {t.name}
                    </option>
                  ))}
                </select>

                <select
                  value={drillParentCol}
                  onChange={(e) => setDrillParentCol(e.target.value)}
                  className="border rounded-lg px-2.5 py-1 font-mono"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  {tables.find((t) => t.name === drillParentTable)?.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>

                <ArrowRight size={13} className="text-zinc-500" />

                <span className="font-bold">Child Table:</span>
                <select
                  value={drillChildTable}
                  onChange={(e) => setDrillChildTable(e.target.value)}
                  className="border rounded-lg px-2.5 py-1 font-semibold"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  {tables.filter((t) => t.name !== drillParentTable).map((t) => (
                    <option key={t.name} value={t.name}>
                      {t.name}
                    </option>
                  ))}
                </select>

                <select
                  value={drillChildCol}
                  onChange={(e) => setDrillChildCol(e.target.value)}
                  className="border rounded-lg px-2.5 py-1 font-mono"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  {tables.find((t) => t.name === drillChildTable)?.columns.map((c) => (
                    <option key={c.name} value={c.name}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                Click any row on the left to instantly inspect matching records on the right.
              </div>
            </div>

            {/* Split Screen Master-Detail Explorer */}
            <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Left Pane: Parent Records */}
              <div
                className="flex flex-col rounded-2xl border overflow-hidden"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="px-4 py-2.5 border-b border-[var(--border)] flex items-center justify-between">
                  <span className="text-xs font-bold">{drillParentTable} (Select a Row)</span>
                  <span className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                    Key: {drillParentCol}
                  </span>
                </div>
                <div className="flex-1 overflow-auto">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="sticky top-0 bg-[var(--surface)] border-b border-[var(--border)]">
                      <tr>
                        {tables.find((t) => t.name === drillParentTable)?.columns.slice(0, 5).map((c) => (
                          <th key={c.name} className="px-3 py-2 font-semibold whitespace-nowrap">
                            {c.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData?.rows && baseTable === drillParentTable ? (
                        previewData.rows.map((r, idx) => {
                          const isSelected = drillSelectedParentRow && drillSelectedParentRow[drillParentCol] === r[drillParentCol];
                          return (
                            <tr
                              key={idx}
                              onClick={() => handleQueryDrillDown(r)}
                              className={`border-b border-[var(--border)] cursor-pointer transition ${
                                isSelected ? "bg-[var(--accent)]/15 font-bold" : "hover:bg-[var(--surface)]"
                              }`}
                            >
                              {tables.find((t) => t.name === drillParentTable)?.columns.slice(0, 5).map((c) => (
                                <td key={c.name} className="px-3 py-2 whitespace-nowrap font-mono text-[11px]">
                                  {r[c.name] !== undefined ? String(r[c.name]) : ""}
                                </td>
                              ))}
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={5} className="p-6 text-center text-zinc-500 text-xs">
                            Run a preview in the Visual Join tab to populate live parent rows.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Right Pane: Child Records */}
              <div
                className="flex flex-col rounded-2xl border overflow-hidden"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="px-4 py-2.5 border-b border-[var(--border)] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold">{drillChildTable} Records</span>
                    {drillResult && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded border border-[var(--border)] text-emerald-400">
                        {drillResult.total_matches} matches ({drillResult.execution_time_ms} ms)
                      </span>
                    )}
                  </div>
                  {drillSelectedParentRow && (
                    <span className="text-[10px] font-mono text-[var(--accent)] font-bold">
                      {drillParentCol} = &quot;{String(drillSelectedParentRow[drillParentCol])}&quot;
                    </span>
                  )}
                </div>

                <div className="flex-1 overflow-auto">
                  {isQueryingDrill ? (
                    <div className="h-full flex items-center justify-center">
                      <RefreshCw size={18} className="animate-spin text-zinc-500" />
                    </div>
                  ) : drillResult ? (
                    drillResult.records.length > 0 ? (
                      <table className="w-full text-xs text-left border-collapse">
                        <thead className="sticky top-0 bg-[var(--surface)] border-b border-[var(--border)]">
                          <tr>
                            {drillResult.columns.map((c) => (
                              <th key={c} className="px-3 py-2 font-semibold whitespace-nowrap">
                                {c}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {drillResult.records.map((r, rIdx) => (
                            <tr key={rIdx} className="border-b border-[var(--border)] hover:bg-[var(--surface)]">
                              {drillResult.columns.map((c) => (
                                <td key={c} className="px-3 py-2 whitespace-nowrap font-mono text-[11px]">
                                  {r[c] !== undefined ? String(r[c]) : ""}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="h-full flex flex-col items-center justify-center p-6 text-center text-zinc-500">
                        <AlertCircle size={20} className="mb-2" />
                        <span className="text-xs font-bold">No matching records found</span>
                        <span className="text-[11px]">
                          Zero rows in &quot;{drillChildTable}&quot; match {drillChildCol} = &quot;{String(drillSelectedParentRow?.[drillParentCol])}&quot;
                        </span>
                      </div>
                    )
                  ) : (
                    <div className="h-full flex items-center justify-center p-6 text-center text-zinc-500 text-xs">
                      Select any row in the master table to drill down into corresponding child records.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 4: DUCKDB SQL STUDIO */}
        {activeStudioView === "sql" && (
          <div className="flex-1 overflow-hidden p-6 flex flex-col gap-4">
            <div
              className="p-4 rounded-2xl border flex flex-col gap-3"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold flex items-center gap-2">
                  <Terminal size={14} style={{ color: "var(--accent)" }} />
                  <span>DuckDB Pushdown Analytical SQL</span>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handlePreview(false)}
                    disabled={executingPreview}
                    className="px-3 py-1.5 rounded-xl text-xs font-bold transition hover:opacity-95 cursor-pointer"
                    style={{ background: "var(--accent)", color: "#fff" }}
                  >
                    {executingPreview ? "Executing..." : "Execute SQL"}
                  </button>
                  <button
                    onClick={handleMaterialize}
                    disabled={materializing || !previewData}
                    className="px-3 py-1.5 rounded-xl text-xs font-bold border border-[var(--border)] hover:bg-emerald-500/10 cursor-pointer disabled:opacity-40"
                  >
                    Materialize Result
                  </button>
                </div>
              </div>

              <textarea
                value={customSql}
                onChange={(e) => setCustomSql(e.target.value)}
                rows={7}
                placeholder="SELECT * FROM table1 JOIN table2 ON table1.id = table2.id..."
                className="w-full font-mono text-xs p-3 rounded-xl border border-[var(--border)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                style={{ background: "var(--surface)", color: "var(--txt)" }}
              />
            </div>

            {/* Results Grid */}
            {previewData && (
              <div
                className="flex-1 overflow-hidden p-4 rounded-2xl border flex flex-col gap-2"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center justify-between pb-1">
                  <span className="text-xs font-bold">Query Result ({previewData.preview_count} rows in {previewData.execution_time_ms} ms)</span>
                </div>
                <div className="flex-1 overflow-auto border border-[var(--border)] rounded-xl">
                  <table className="w-full text-xs text-left border-collapse">
                    <thead className="sticky top-0 bg-[var(--surface)] border-b border-[var(--border)]">
                      <tr>
                        {previewData.columns.map((c) => (
                          <th key={c.name} className="px-3 py-2 font-semibold whitespace-nowrap">
                            {c.name}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.rows.map((r, rIdx) => (
                        <tr key={rIdx} className="border-b border-[var(--border)] hover:bg-[var(--surface)]">
                          {previewData.columns.map((c) => (
                            <td key={c.name} className="px-3 py-1.5 font-mono whitespace-nowrap">
                              {r[c.name] !== null && r[c.name] !== undefined ? String(r[c.name]) : "NULL"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── MODAL 1: MULTI-SHEET & TABLE INGESTION ────────────────────────── */}
      {showIngestModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div
            className="w-full max-w-2xl rounded-2xl border shadow-2xl flex flex-col overflow-hidden"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <FileSpreadsheet size={16} style={{ color: "var(--accent)" }} />
                <span className="text-sm font-bold">Add Sheets & Tables</span>
              </div>
              <button
                onClick={() => setShowIngestModal(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-[var(--txt)]"
              >
                <X size={16} />
              </button>
            </div>

            {/* Source Segmented Tabs */}
            <div className="flex items-center border-b border-[var(--border)] px-4 pt-2 gap-2">
              {[
                { id: "local", label: "Local File (.xlsx, .csv, .parquet)", count: inspectedFileSheets.length },
                { id: "companion", label: "Current Workbook Sheets", count: companionOrigin?.unimported_sheets?.length || 0 },
                { id: "cloud", label: "Cloud Sheet (Google / OneDrive)", count: cloudSheets.length },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setIngestTab(tab.id as any)}
                  className={`pb-2 px-3 text-xs font-bold border-b-2 transition cursor-pointer ${
                    ingestTab === tab.id
                      ? "border-[var(--accent)] text-[var(--txt)]"
                      : "border-transparent text-[var(--txt-m)] hover:text-[var(--txt)]"
                  }`}
                >
                  <span>{tab.label}</span>
                  {tab.count > 0 && (
                    <span className="ml-1.5 px-1.5 py-0.2 rounded text-[10px] font-mono bg-zinc-800 text-zinc-300">
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Modal Body */}
            <div className="p-6 flex flex-col gap-4 max-h-[60vh] overflow-y-auto">
              {/* TAB 1: LOCAL FILE */}
              {ingestTab === "local" && (
                <div className="flex flex-col gap-4">
                  <div className="border border-dashed border-[var(--border)] rounded-2xl p-6 text-center flex flex-col items-center justify-center gap-2">
                    <Upload size={24} className="text-zinc-400" />
                    <span className="text-xs font-bold">Choose an Excel (.xlsx, .xls) or CSV / Parquet file</span>
                    <input
                      type="file"
                      accept=".xlsx,.xls,.csv,.parquet,.json"
                      onChange={handleFileSelect}
                      className="text-xs text-zinc-400 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-[var(--accent)] file:text-white hover:file:opacity-90 cursor-pointer"
                    />
                  </div>

                  {isInspectingFile && (
                    <div className="flex items-center justify-center gap-2 py-4 text-xs text-zinc-400">
                      <RefreshCw size={14} className="animate-spin" />
                      <span>Inspecting multi-sheet workbook structure...</span>
                    </div>
                  )}

                  {inspectedFileSheets.length > 0 && (
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-bold">Detected Worksheets ({inspectedFileSheets.length}):</span>
                      <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
                        {inspectedFileSheets.map((s) => (
                          <div
                            key={s.sheet_name}
                            className="flex items-center justify-between p-2.5 rounded-xl border border-[var(--border)]"
                            style={{ background: "var(--surface)" }}
                          >
                            <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                              <input
                                type="checkbox"
                                checked={Boolean(selectedSheetsToImport[s.sheet_name])}
                                onChange={(e) =>
                                  setSelectedSheetsToImport({
                                    ...selectedSheetsToImport,
                                    [s.sheet_name]: e.target.checked,
                                  })
                                }
                              />
                              <span>{s.sheet_name}</span>
                              {s.row_count > 0 && (
                                <span className="text-[10px] font-mono text-zinc-400">
                                  ({s.row_count.toLocaleString()} rows)
                                </span>
                              )}
                            </label>

                            <input
                              type="text"
                              value={customTableNames[s.sheet_name] || s.table_name}
                              onChange={(e) =>
                                setCustomTableNames({
                                  ...customTableNames,
                                  [s.sheet_name]: e.target.value,
                                })
                              }
                              placeholder="Table name..."
                              className="text-xs px-2 py-1 rounded border border-[var(--border)] font-mono w-36 bg-[var(--card)]"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: COMPANION SHEETS FROM WORKSPACE ORIGIN */}
              {ingestTab === "companion" && (
                <div className="flex flex-col gap-3">
                  {companionOrigin?.has_companion_sheets && companionOrigin.unimported_sheets.length > 0 ? (
                    <>
                      <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/10 text-xs">
                        <span className="font-bold">Original Workbook Detected: </span>
                        <span>
                          {companionOrigin.unimported_sheets.length} worksheet(s) in the original upload have not been imported yet.
                        </span>
                      </div>
                      <div className="flex flex-col gap-2">
                        {companionOrigin.unimported_sheets.map((s) => (
                          <div
                            key={s.sheet_name}
                            className="flex items-center justify-between p-2.5 rounded-xl border border-[var(--border)]"
                            style={{ background: "var(--surface)" }}
                          >
                            <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                              <input
                                type="checkbox"
                                checked={Boolean(selectedSheetsToImport[s.sheet_name])}
                                onChange={(e) =>
                                  setSelectedSheetsToImport({
                                    ...selectedSheetsToImport,
                                    [s.sheet_name]: e.target.checked,
                                  })
                                }
                              />
                              <span>{s.sheet_name}</span>
                              {s.columns.length > 0 && (
                                <span className="text-[10px] font-mono text-zinc-400">
                                  ({s.columns.length} columns)
                                </span>
                              )}
                            </label>

                            <input
                              type="text"
                              value={customTableNames[s.sheet_name] || s.table_name}
                              onChange={(e) =>
                                setCustomTableNames({
                                  ...customTableNames,
                                  [s.sheet_name]: e.target.value,
                                })
                              }
                              className="text-xs px-2 py-1 rounded border border-[var(--border)] font-mono w-36 bg-[var(--card)]"
                            />
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <div className="p-6 text-center text-zinc-500 text-xs">
                      No companion worksheets detected from original workspace upload. Use the Local File tab to upload a new workbook.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: CLOUD SHEET */}
              {ingestTab === "cloud" && (
                <div className="flex flex-col gap-4">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      placeholder="Paste Google Sheets or OneDrive link..."
                      value={cloudUrl}
                      onChange={(e) => setCloudUrl(e.target.value)}
                      className="flex-1 px-3 py-2 text-xs rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--txt)]"
                    />
                    <button
                      onClick={handleInspectCloud}
                      disabled={isInspectingCloud || !cloudUrl.trim()}
                      className="px-3 py-2 rounded-xl text-xs font-bold transition hover:opacity-90 cursor-pointer"
                      style={{ background: "var(--accent)", color: "#fff" }}
                    >
                      {isInspectingCloud ? <RefreshCw size={13} className="animate-spin" /> : "Inspect"}
                    </button>
                  </div>

                  {cloudSheets.length > 0 && (
                    <div className="flex flex-col gap-2">
                      <span className="text-xs font-bold">Available Cloud Tabs ({cloudSheets.length}):</span>
                      <div className="flex flex-col gap-2 max-h-48 overflow-y-auto">
                        {cloudSheets.map((s) => (
                          <div
                            key={s.sheet_name}
                            className="flex items-center justify-between p-2.5 rounded-xl border border-[var(--border)]"
                            style={{ background: "var(--surface)" }}
                          >
                            <label className="flex items-center gap-2 text-xs font-medium cursor-pointer">
                              <input
                                type="checkbox"
                                checked={Boolean(selectedSheetsToImport[s.sheet_name])}
                                onChange={(e) =>
                                  setSelectedSheetsToImport({
                                    ...selectedSheetsToImport,
                                    [s.sheet_name]: e.target.checked,
                                  })
                                }
                              />
                              <span>{s.sheet_name}</span>
                            </label>

                            <input
                              type="text"
                              value={customTableNames[s.sheet_name] || s.table_name}
                              onChange={(e) =>
                                setCustomTableNames({
                                  ...customTableNames,
                                  [s.sheet_name]: e.target.value,
                                })
                              }
                              className="text-xs px-2 py-1 rounded border border-[var(--border)] font-mono w-36 bg-[var(--card)]"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-[var(--border)] flex items-center justify-end gap-2">
              <button
                onClick={() => setShowIngestModal(false)}
                className="px-3 py-1.5 rounded-xl text-xs font-semibold border border-[var(--border)] hover:bg-zinc-800"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteImport}
                disabled={isImportingSheets}
                className="px-4 py-1.5 rounded-xl text-xs font-bold transition hover:opacity-90 cursor-pointer"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                {isImportingSheets ? "Importing..." : "Import Selected Worksheets"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── MODAL 2: REFERENTIAL INTEGRITY AUDIT DRAWER ───────────────────── */}
      {showAuditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div
            className="w-full max-w-xl rounded-2xl border shadow-2xl flex flex-col overflow-hidden"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-[var(--border)]">
              <div className="flex items-center gap-2">
                <ShieldCheck size={16} className="text-emerald-500" />
                <span className="text-sm font-bold">Referential Integrity Audit</span>
              </div>
              <button onClick={() => setShowAuditModal(false)} className="p-1 rounded-lg text-zinc-400 hover:text-[var(--txt)]">
                <X size={16} />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 flex flex-col gap-4 max-h-[70vh] overflow-y-auto">
              {isRunningAudit ? (
                <div className="py-12 flex flex-col items-center justify-center gap-2 text-zinc-400">
                  <RefreshCw size={24} className="animate-spin text-[var(--accent)]" />
                  <span className="text-xs font-medium">Auditing keys with DuckDB in-memory engine...</span>
                </div>
              ) : auditResult ? (
                <div className="flex flex-col gap-4">
                  {/* Score & Relationship Summary */}
                  <div
                    className="p-4 rounded-xl border flex items-center justify-between"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <div>
                      <div className="text-xs font-bold">
                        {auditResult.left_table}.{auditResult.left_column} → {auditResult.right_table}.{auditResult.right_column}
                      </div>
                      <div className="text-[11px] text-zinc-400">
                        Cardinality: <span className="font-mono font-bold text-zinc-200">{auditResult.referential_metrics.cardinality}</span>
                      </div>
                    </div>

                    <div className="flex flex-col items-end">
                      <span className="text-2xl font-black font-mono text-emerald-400">
                        {auditResult.referential_metrics.health_score}%
                      </span>
                      <span className="text-[9px] uppercase tracking-wider text-zinc-400 font-bold">Health Score</span>
                    </div>
                  </div>

                  {/* Metrics Grid */}
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div className="p-3 rounded-xl border border-[var(--border)]" style={{ background: "var(--surface)" }}>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">Matched Keys</span>
                      <div className="text-lg font-bold font-mono text-emerald-300 mt-1">
                        {auditResult.referential_metrics.matched_keys_count.toLocaleString()}
                        <span className="text-xs text-zinc-400 font-normal ml-1.5">
                          ({auditResult.referential_metrics.match_percentage}%)
                        </span>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl border border-[var(--border)]" style={{ background: "var(--surface)" }}>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">Orphan Keys (Missing)</span>
                      <div className="text-lg font-bold font-mono text-rose-300 mt-1">
                        {auditResult.referential_metrics.orphan_keys_count.toLocaleString()}
                        <span className="text-xs text-zinc-400 font-normal ml-1.5">
                          ({auditResult.referential_metrics.orphan_percentage}%)
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Fan-Out Risk Alert */}
                  {auditResult.referential_metrics.fan_out_risk === "high" && (
                    <div className="p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-200 text-xs flex items-start gap-2">
                      <ShieldAlert size={16} className="text-rose-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">High Fan-Out Multiplication Risk: </span>
                        <span>
                          Many-to-Many cardinality detected. Joining directly will duplicate rows and inflate numerical sums. Use Pre-Join Rollup on the target table.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Orphan Sample Values */}
                  {auditResult.referential_metrics.orphan_samples?.length > 0 && (
                    <div className="flex flex-col gap-1.5">
                      <span className="text-xs font-bold">Sample Orphan Keys in {auditResult.left_table}:</span>
                      <div className="flex flex-wrap gap-1.5">
                        {auditResult.referential_metrics.orphan_samples.map((k, i) => (
                          <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/60 text-rose-300 border border-rose-800">
                            {k}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommendations */}
                  <div className="flex flex-col gap-1.5 pt-2 border-t border-[var(--border)]">
                    <span className="text-xs font-bold">Recommendations:</span>
                    <ul className="text-xs list-disc pl-4 space-y-1 text-zinc-300">
                      {auditResult.recommendations.map((rec, i) => (
                        <li key={i}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : null}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-[var(--border)] flex justify-end">
              <button
                onClick={() => setShowAuditModal(false)}
                className="px-4 py-1.5 rounded-xl text-xs font-bold"
                style={{ background: "var(--accent)", color: "#fff" }}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Re-export as JoinCanvasTab for backwards compatibility
export const JoinCanvasTab = MultiSheetTab;
