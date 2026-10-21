"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";
import {
  SupabaseLogo,
  PostgresLogo,
  MySQLLogo,
  SnowflakeLogo,
  BigQueryLogo,
  ClickHouseLogo,
  DatabricksLogo,
  AWSS3Logo,
  GCSLogo,
  AzureBlobLogo,
  CSVLogo,
  ExcelLogo,
  ParquetLogo,
  JSONLogo,
  GoogleSheetsLogo,
  MicrosoftExcelOnlineLogo,
} from "./DataLogos";
import { SAMPLE_DATASETS, SampleDataset } from "./sampleDatasets";
import Logo from "../Logo";
import {
  Zap,
  Search,
  ChevronDown,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  UploadCloud,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  Database,
  Layers,
  Bot,
  Cpu,
  Rocket,
} from "lucide-react";

interface WorkspaceLaunchModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: string;
  initialConnectorId?: string;
}

type ConnectorCategory = "spreadsheets" | "warehouses" | "relational" | "storage" | "files";

interface ConnectorDef {
  id: string;
  name: string;
  category: ConnectorCategory;
  subtitle: string;
  tag?: string;
  defaultUri: string;
  targetTable: string;
  Logo: React.ComponentType<{ size?: number; className?: string }>;
}

const ALL_CONNECTORS: ConnectorDef[] = [
  // Online Spreadsheets & Cloud Links
  {
    id: "google_sheets",
    name: "Google Sheets",
    category: "spreadsheets",
    subtitle: "Public / Shared Link",
    tag: "URL Link",
    defaultUri: "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
    targetTable: "Sheet1",
    Logo: GoogleSheetsLogo,
  },
  {
    id: "excel_online",
    name: "Microsoft 365 / Excel",
    category: "spreadsheets",
    subtitle: "OneDrive / SharePoint Link",
    tag: "Office 365",
    defaultUri: "https://onedrive.live.com/view.aspx?resid=EXAMPLE&ithint=file%2cxlsx",
    targetTable: "Sheet1",
    Logo: MicrosoftExcelOnlineLogo,
  },

  // Cloud Warehouses
  {
    id: "snowflake",
    name: "Snowflake",
    category: "warehouses",
    subtitle: "Cloud Data Warehouse",
    defaultUri: "snowflake://analytics_user:***@account.snowflakecomputing.com/prod_db/public?warehouse=compute_wh",
    targetTable: "public.analytics_events",
    Logo: SnowflakeLogo,
  },
  {
    id: "bigquery",
    name: "BigQuery",
    category: "warehouses",
    subtitle: "Google Cloud / Serverless",
    defaultUri: "bigquery://gcp-project-prod/analytics_dataset",
    targetTable: "user_conversions",
    Logo: BigQueryLogo,
  },
  {
    id: "databricks",
    name: "Databricks",
    category: "warehouses",
    subtitle: "Delta Lake / Spark Engine",
    defaultUri: "databricks://token:***@dbc-12345.cloud.databricks.com:443/default",
    targetTable: "gold_metrics",
    Logo: DatabricksLogo,
  },

  // Relational DBs
  {
    id: "postgresql",
    name: "PostgreSQL",
    category: "relational",
    subtitle: "PostgreSQL / Supabase",
    tag: "v12-16",
    defaultUri: "postgresql://postgres:***@db.project-ref.supabase.co:5432/postgres",
    targetTable: "public.users",
    Logo: PostgresLogo,
  },
  {
    id: "mysql",
    name: "MySQL",
    category: "relational",
    subtitle: "Relational / InnoDB",
    tag: "v8.0+",
    defaultUri: "mysql+pymysql://admin:***@mysql.us-east-1.rds.amazonaws.com:3306/production",
    targetTable: "orders",
    Logo: MySQLLogo,
  },
  {
    id: "clickhouse",
    name: "ClickHouse",
    category: "relational",
    subtitle: "Columnar OLAP",
    defaultUri: "clickhouse+native://default:***@service.us-east-1.clickhouse.cloud:9440/default",
    targetTable: "telemetry_logs",
    Logo: ClickHouseLogo,
  },

  // Cloud Storage
  {
    id: "aws_s3",
    name: "AWS S3",
    category: "storage",
    subtitle: "Amazon S3 Bucket",
    defaultUri: "s3://dataforge-analytics/2026/events.parquet",
    targetTable: "events.parquet",
    Logo: AWSS3Logo,
  },
  {
    id: "gcs",
    name: "GCS",
    category: "storage",
    subtitle: "Google Cloud Storage",
    defaultUri: "gs://analytics-bucket/lakehouse/transactions.parquet",
    targetTable: "transactions.parquet",
    Logo: GCSLogo,
  },
  {
    id: "azure_blob",
    name: "Azure Blob",
    category: "storage",
    subtitle: "Azure Blob Storage",
    defaultUri: "az://storage-account/container/sales.parquet",
    targetTable: "sales.parquet",
    Logo: AzureBlobLogo,
  },

  // Local Files
  {
    id: "csv",
    name: "CSV",
    category: "files",
    subtitle: "Comma Separated Values",
    defaultUri: "dataset.csv",
    targetTable: "dataset.csv",
    Logo: CSVLogo,
  },
  {
    id: "excel",
    name: "Excel",
    category: "files",
    subtitle: "Microsoft Excel (.xlsx)",
    defaultUri: "report.xlsx",
    targetTable: "Sheet1",
    Logo: ExcelLogo,
  },
  {
    id: "parquet",
    name: "Parquet",
    category: "files",
    subtitle: "Apache Parquet",
    defaultUri: "events.parquet",
    targetTable: "events.parquet",
    Logo: ParquetLogo,
  },
  {
    id: "json",
    name: "JSON",
    category: "files",
    subtitle: "JSON Records",
    defaultUri: "records.json",
    targetTable: "records.json",
    Logo: JSONLogo,
  },
];

/* ── Input Sanitizer & Validator ── */
function sanitizeInput(raw: string): string {
  if (!raw) return "";
  // Strip control characters and leading/trailing whitespace
  return raw.replace(/[\x00-\x1F\x7F]/g, "").trim();
}

interface FormatConfig {
  label: string;
  extensions: string[];
  accept: string;
  hint: string;
}

function getExpectedExtensions(connectorId: string): FormatConfig {
  switch (connectorId) {
    case "csv":
      return {
        label: "CSV",
        extensions: ["csv"],
        accept: ".csv",
        hint: "Supports CSV datasets (.csv, max 100MB)",
      };
    case "excel":
      return {
        label: "Excel",
        extensions: ["xlsx", "xls"],
        accept: ".xlsx,.xls",
        hint: "Supports Microsoft Excel workbooks (.xlsx, .xls, max 100MB)",
      };
    case "parquet":
      return {
        label: "Parquet",
        extensions: ["parquet"],
        accept: ".parquet",
        hint: "Supports Apache Parquet columnar datasets (.parquet, max 100MB)",
      };
    case "json":
      return {
        label: "JSON",
        extensions: ["json", "jsonl", "ndjson"],
        accept: ".json,.jsonl,.ndjson",
        hint: "Supports JSON records & lines (.json, .jsonl, .ndjson, max 100MB)",
      };
    default:
      return {
        label: "Dataset",
        extensions: ["csv", "xlsx", "xls", "parquet", "json", "jsonl", "ndjson"],
        accept: ".csv,.xlsx,.xls,.parquet,.json",
        hint: "Supports CSV, Excel (.xlsx), Parquet, JSON (max 100MB)",
      };
  }
}

function validateConnectorInput(
  connectorId: string,
  category: ConnectorCategory,
  uri: string,
  file: File | null
): { valid: boolean; error?: string } {
  if (category === "files") {
    const config = getExpectedExtensions(connectorId);
    if (!file) {
      return {
        valid: false,
        error: `Please select or drop a ${config.label} dataset file (${config.extensions.map((e) => `.${e}`).join(", ")}) to upload.`,
      };
    }
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    if (!ext || !config.extensions.includes(ext)) {
      let suggestedConnector = "";
      if (ext === "csv") suggestedConnector = "CSV";
      else if (["xlsx", "xls"].includes(ext)) suggestedConnector = "Excel";
      else if (ext === "parquet") suggestedConnector = "Parquet";
      else if (["json", "jsonl", "ndjson"].includes(ext)) suggestedConnector = "JSON";

      const suggestionText = suggestedConnector
        ? ` Please switch to '${suggestedConnector}' or upload a .${config.extensions.join(" / .")} file.`
        : ` Please upload a .${config.extensions.join(" / .")} file.`;

      return {
        valid: false,
        error: `File extension mismatch: '${file.name}' is a .${ext || "unknown"} file, but '${config.label}' is selected.${suggestionText}`,
      };
    }
    if (file.size > 100 * 1024 * 1024) {
      return { valid: false, error: "File exceeds 100MB limit. Connect via cloud storage or warehouse." };
    }
    return { valid: true };
  }

  const clean = sanitizeInput(uri);
  if (!clean) {
    return { valid: false, error: "Connection link or URI is required." };
  }

  if (connectorId === "google_sheets") {
    if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
      return { valid: false, error: "URL must start with https://" };
    }
    if (!clean.includes("docs.google.com/spreadsheets")) {
      return {
        valid: false,
        error: "Invalid Google Sheets URL. Expected format: https://docs.google.com/spreadsheets/d/...",
      };
    }
    return { valid: true };
  }

  if (connectorId === "excel_online") {
    if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
      return { valid: false, error: "URL must start with https://" };
    }
    const isM365 =
      clean.includes("onedrive.live.com") ||
      clean.includes("1drv.ms") ||
      clean.includes("sharepoint.com") ||
      clean.toLowerCase().endsWith(".xlsx");
    if (!isM365) {
      return {
        valid: false,
        error: "Invalid link. Expected OneDrive, SharePoint, or direct .xlsx URL.",
      };
    }
    return { valid: true };
  }

  if (category === "relational" || category === "warehouses" || category === "storage") {
    if (!clean.includes("://") && !clean.startsWith("gs://") && !clean.startsWith("s3://") && !clean.startsWith("az://")) {
      return {
        valid: false,
        error: "Invalid URI syntax. Example: postgresql://user:pass@host:5432/dbname",
      };
    }
    return { valid: true };
  }

  return { valid: true };
}

export default function WorkspaceLaunchModal({
  isOpen,
  onClose,
  initialConnectorId,
}: WorkspaceLaunchModalProps) {
  const router = useRouter();
  const { user } = useAuth();

  // Selected Connector (defaults to initialConnectorId or PostgreSQL)
  const [selectedConnector, setSelectedConnector] = useState<ConnectorDef>(() => {
    if (initialConnectorId) {
      const match = ALL_CONNECTORS.find((c) => c.id === initialConnectorId);
      if (match) return match;
    }
    return ALL_CONNECTORS.find((c) => c.id === "postgresql") || ALL_CONNECTORS[0];
  });

  // Search & Category Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<"all" | ConnectorCategory>("all");
  const [isCategoryDropdownOpen, setIsCategoryDropdownOpen] = useState(false);

  // Connection inputs (start empty so user is required to enter valid input)
  const [connUri, setConnUri] = useState("");
  const [targetTable, setTargetTable] = useState("");

  // Test Connection status
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [dbTables, setDbTables] = useState<string[]>([]);
  const [sheetTabs, setSheetTabs] = useState<string[]>([]);
  const [isDetectingTabs, setIsDetectingTabs] = useState(false);

  // File Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Ingestion / Launching State
  const [isConnecting, setIsConnecting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isGeneratingWorkspace, setIsGeneratingWorkspace] = useState(false);
  const [generationStage, setGenerationStage] = useState(1);
  const [generationProgress, setGenerationProgress] = useState(15);
  const [generationStatus, setGenerationStatus] = useState("Ingesting dataset and authenticating data connection...");

  const handleDetectSheetTabs = async (urlToTest?: string) => {
    const rawUrl = urlToTest !== undefined ? urlToTest : connUri;
    const clean = sanitizeInput(rawUrl);
    if (!clean) return;

    const isGoogle = clean.includes("docs.google.com/spreadsheets");
    const isMicrosoft =
      clean.includes("1drv.ms") ||
      clean.includes("onedrive.live.com") ||
      clean.includes("sharepoint.com") ||
      clean.includes("office.com") ||
      clean.includes("office365.com") ||
      clean.includes(".xlsx") ||
      clean.includes(".xls");

    if (!isGoogle && !isMicrosoft && selectedConnector.category !== "spreadsheets") {
      return;
    }

    setIsDetectingTabs(true);
    try {
      const endpoint = isMicrosoft ? "/upload/excel-online/worksheets" : "/upload/sheets/worksheets";
      const res = await apiFetch(endpoint, {
        method: "POST",
        body: JSON.stringify({ url: clean }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.sheets && Array.isArray(data.sheets) && data.sheets.length > 0) {
          setSheetTabs(data.sheets);
          if (!targetTable || !data.sheets.includes(targetTable)) {
            setTargetTable(data.sheets[0]);
          }
        }
      }
    } catch {
      // non-blocking tab detection failure
    } finally {
      setIsDetectingTabs(false);
    }
  };

  React.useEffect(() => {
    const isOnlineSpreadsheet = selectedConnector.id === "google_sheets" || selectedConnector.id === "excel_online";
    if (isOnlineSpreadsheet && connUri.trim()) {
      const isCandidateUrl =
        connUri.includes("docs.google.com/spreadsheets") ||
        connUri.includes("1drv.ms") ||
        connUri.includes("onedrive.live.com") ||
        connUri.includes("sharepoint.com") ||
        connUri.includes("office.com") ||
        connUri.includes("office365.com") ||
        connUri.includes(".xlsx") ||
        connUri.includes(".xls");

      if (isCandidateUrl) {
        const timer = setTimeout(() => {
          handleDetectSheetTabs(connUri);
        }, 500);
        return () => clearTimeout(timer);
      }
    } else if (!isOnlineSpreadsheet) {
      setSheetTabs([]);
    }
  }, [connUri, selectedConnector.id]);

  React.useEffect(() => {
    if (isOpen && initialConnectorId) {
      const match = ALL_CONNECTORS.find((c) => c.id === initialConnectorId);
      if (match) {
        setSelectedConnector(match);
        setConnUri("");
        setTargetTable("");
        setSheetTabs([]);
        setSelectedCategory(match.category);
      }
    }
  }, [isOpen, initialConnectorId]);

  // Ensure default role is Admin whenever modal is opened
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("df_user_role", "Admin");
    }
  }, [isOpen]);

  const handleSelectConnector = (connector: ConnectorDef) => {
    setSelectedConnector(connector);
    setConnUri("");
    setTargetTable("");
    setSelectedFile(null);
    setTestResult(null);
    setDbTables([]);
    setSheetTabs([]);
    setErrorMsg("");
  };

  const filteredConnectors = ALL_CONNECTORS.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.subtitle.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === "all" || c.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const spreadsheets = filteredConnectors.filter((c) => c.category === "spreadsheets");
  const warehouses = filteredConnectors.filter((c) => c.category === "warehouses");
  const relationalDbs = filteredConnectors.filter((c) => c.category === "relational");
  const cloudStorage = filteredConnectors.filter((c) => c.category === "storage");
  const localFiles = filteredConnectors.filter((c) => c.category === "files");

  const handleTestPing = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const cleanUri = sanitizeInput(connUri);
      const res = await apiFetch("/upload/database/test", {
        method: "POST",
        body: JSON.stringify({ connection_string: cleanUri }),
      });
      const data = await res.json();
      if (!res.ok) {
        const errMsg = data.detail || data.message || `Database test failed (HTTP ${res.status})`;
        setTestResult({
          ok: false,
          message: errMsg,
        });
        return;
      }
      setTestResult({
        ok: Boolean(data.ok),
        message: data.message || (data.ok ? "Connected" : "Failed to connect"),
      });

      if (data.ok) {
        const tablesRes = await apiFetch("/upload/database/tables", {
          method: "POST",
          body: JSON.stringify({ connection_string: cleanUri }),
        });
        if (tablesRes.ok) {
          const tData = await tablesRes.json();
          if (tData.tables && tData.tables.length > 0) {
            setDbTables(tData.tables);
            setTargetTable(tData.tables[0]);
          }
        }
      }
    } catch (err: any) {
      setTestResult({
        ok: false,
        message: err.message || "Network error",
      });
    } finally {
      setIsTesting(false);
    }
  };

  const executeIngestion = async () => {
    setIsConnecting(true);
    setIsGeneratingWorkspace(true);
    setGenerationStage(1);
    setGenerationProgress(25);
    setGenerationStatus(`Connecting to ${selectedConnector.name} and initiating data ingestion...`);
    setErrorMsg("");

    try {
      let uploadId = "";
      const cleanUri = sanitizeInput(connUri);
      const cleanTable = sanitizeInput(targetTable);

      if (selectedConnector.category === "spreadsheets") {
        if (selectedConnector.id === "google_sheets") {
          setGenerationStatus("Streaming Google Sheets workbook tabs...");
          const res = await apiFetch("/upload/sheets", {
            method: "POST",
            body: JSON.stringify({
              url: cleanUri,
              sheet_name: cleanTable || undefined,
            }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Google Sheets ingestion failed" }));
            throw new Error(err.detail || err.error || "Google Sheets ingestion failed. Ensure document is set to 'Anyone with link can view'.");
          }
          const data = await res.json();
          uploadId = data.upload_id;
        } else {
          // excel_online
          setGenerationStatus("Accessing Microsoft Excel Online workbook...");
          const res = await apiFetch("/upload/excel-online", {
            method: "POST",
            body: JSON.stringify({
              url: cleanUri,
              sheet_name: cleanTable || undefined,
            }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Microsoft Excel Online ingestion failed" }));
            throw new Error(err.detail || err.error || "Microsoft Excel Online ingestion failed. Ensure public view link is active.");
          }
          const data = await res.json();
          uploadId = data.upload_id;
        }
      } else if (selectedConnector.category === "files") {
        if (!selectedFile) {
          throw new Error("No file selected. Please choose or drag a dataset file (.csv, .xlsx, .parquet, or .json).");
        }

        setGenerationStatus(`Ingesting and parsing ${selectedFile.name}...`);
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("expected_format", selectedConnector.id);
        const res = await apiFetch("/upload", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Upload failed" }));
          throw new Error(err.detail || "File processing failed. Please verify file integrity.");
        }
        const data = await res.json();
        uploadId = data.upload_id;
      } else {
        setGenerationStatus(`Executing database ingest query on ${selectedConnector.name}...`);
        const payload: any = {
          connection_string: cleanUri,
          limit: 5000,
          dataset_name: `${selectedConnector.name.toLowerCase()}_${cleanTable || "dataset"}.csv`,
          table_name: cleanTable || "public.users",
        };

        const res = await apiFetch("/upload/database/ingest", {
          method: "POST",
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Database connection failed" }));
          throw new Error(err.detail || err.error || "Database ingestion failed. Check your connection string and credentials.");
        }
        const data = await res.json();
        uploadId = data.upload_id;
      }

      // Stage 4: Ingestion complete — enter workspace immediately
      setGenerationStage(4);
      setGenerationProgress(100);
      setGenerationStatus("Dataset ready! Launching workspace...");

      if (typeof window !== "undefined") {
        localStorage.setItem("df_user_role", "Admin");
        localStorage.setItem("df_last_upload_id", uploadId);
      }

      await new Promise((r) => setTimeout(r, 80));

      // Direct navigation to workspace — DO NOT call onClose() to eliminate landing page flash
      if (typeof window !== "undefined") {
        window.location.href = `/workspace?upload_id=${encodeURIComponent(uploadId)}`;
      } else {
        router.push(`/workspace?upload_id=${encodeURIComponent(uploadId)}`);
      }
    } catch (err: any) {
      setIsGeneratingWorkspace(false);
      setIsConnecting(false);
      setErrorMsg(err.message || "Connection failed");
    }
  };

  const handleConnect = async () => {
    setErrorMsg("");

    // Sanitize and Validate inputs
    const check = validateConnectorInput(
      selectedConnector.id,
      selectedConnector.category,
      connUri,
      selectedFile
    );

    if (!check.valid) {
      setErrorMsg(check.error || "Invalid input.");
      return;
    }

    // By default people are Admin — proceed directly to workspace generation
    await executeIngestion();
  };

  const handleIncomingFile = (file: File) => {
    setErrorMsg("");
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    const config = getExpectedExtensions(selectedConnector.id);

    if (!ext || !config.extensions.includes(ext)) {
      let suggestedConnector = "";
      if (ext === "csv") suggestedConnector = "CSV";
      else if (["xlsx", "xls"].includes(ext)) suggestedConnector = "Excel";
      else if (ext === "parquet") suggestedConnector = "Parquet";
      else if (["json", "jsonl", "ndjson"].includes(ext)) suggestedConnector = "JSON";

      const suggestionText = suggestedConnector
        ? ` Please switch to '${suggestedConnector}' or upload a .${config.extensions.join(" / .")} file.`
        : ` Please upload a .${config.extensions.join(" / .")} file.`;

      setErrorMsg(
        `File extension mismatch: '${file.name}' is a .${ext || "unknown"} file, but '${selectedConnector.name}' is selected.${suggestionText}`
      );
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    if (file.size > 100 * 1024 * 1024) {
      setErrorMsg("File exceeds 100MB limit. Connect via cloud storage or warehouse.");
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setSelectedFile(file);
    setErrorMsg("");
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleIncomingFile(e.dataTransfer.files[0]);
    }
  };

  const handleQuickSample = (sample: SampleDataset) => {
    const csvConnector = ALL_CONNECTORS.find((c) => c.id === "csv") || selectedConnector;
    setSelectedConnector(csvConnector);
    const blob = new Blob([sample.csvContent], { type: "text/csv" });
    const file = new File([blob], sample.filename, { type: "text/csv" });
    setSelectedFile(file);
    setErrorMsg("");
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-5 backdrop-blur-md animate-fadeIn"
      style={{ background: "rgba(0, 0, 0, 0.72)" }}
      onClick={isGeneratingWorkspace ? undefined : onClose}
    >
      <div
        className="w-full max-w-4xl rounded-2xl shadow-2xl overflow-hidden flex flex-col relative animate-slideUp transition-colors"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
          color: "var(--txt)",
          boxShadow: "0 25px 60px -15px rgba(0,0,0,0.5), 0 0 30px var(--glow)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Minimal Header ── */}
        <div
          className="px-5 py-3.5 border-b flex items-center justify-between shrink-0"
          style={{
            borderColor: "var(--border)",
            background: "var(--nav)",
          }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border"
              style={{
                background: "var(--glow)",
                borderColor: "var(--accent)",
              }}
            >
              <Logo size={20} showText={false} />
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight" style={{ color: "var(--txt)" }}>
                {isGeneratingWorkspace ? "Generating Workspace" : "Ingestion Hub"}
              </h3>
              <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                {isGeneratingWorkspace
                  ? "DataForge High-Performance Analytics Engine"
                  : "Connect your data source or upload a dataset to launch your workspace."}
              </p>
            </div>
          </div>

          {!isGeneratingWorkspace && (
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-lg border flex items-center justify-center transition-all cursor-pointer opacity-80 hover:opacity-100"
              style={{
                borderColor: "var(--border)",
                background: "var(--card)",
                color: "var(--txt-m)",
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {isGeneratingWorkspace ? (
          <div className="relative p-8 sm:p-14 min-h-[440px] flex flex-col items-center justify-center text-center overflow-hidden">
            {/* Ambient atmospheric glow behind animation */}
            <div
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[460px] h-[300px] rounded-full blur-[110px] pointer-events-none opacity-25"
              style={{ background: "radial-gradient(circle, var(--accent) 0%, #ff7043 55%, transparent 70%)" }}
            />

            {/* Glowing Orbital Ring Centerpiece */}
            <div className="relative mb-6 flex items-center justify-center">
              {/* Outer ring: spins dashed during generation, settles into calm glowing emerald solid border when ready */}
              <div
                className={`w-24 h-24 rounded-full border-2 transition-all duration-500 ${
                  generationStage === 4 ? "border-solid" : "border-dashed animate-spin"
                }`}
                style={{
                  borderColor: generationStage === 4 ? "rgba(16, 185, 129, 0.45)" : "var(--accent)",
                  animationDuration: generationStage === 4 ? "0s" : "9s",
                  boxShadow: generationStage === 4 ? "0 0 35px rgba(16, 185, 129, 0.35)" : "0 0 35px var(--glow)",
                }}
              />
              {/* Mid pulsating ring - active only during initial synthesis stages */}
              {generationStage < 4 && (
                <div
                  className="absolute w-20 h-20 rounded-full border border-orange-400/30 animate-ping opacity-25"
                />
              )}
              {/* Center icon badge - replaced moving bouncing tick with stable Rocket emblem */}
              <div
                className="absolute w-14 h-14 rounded-2xl flex items-center justify-center text-white shadow-2xl border transition-all duration-500"
                style={{
                  background: generationStage === 4 ? "linear-gradient(135deg, #10b981, #059669)" : "var(--surface)",
                  borderColor: generationStage === 4 ? "rgba(255, 255, 255, 0.3)" : "var(--border)",
                  boxShadow: generationStage === 4 ? "0 0 30px rgba(16, 185, 129, 0.45)" : "0 0 25px var(--glow)",
                }}
              >
                {generationStage === 4 ? (
                  <div className="flex items-center justify-center">
                    <Rocket size={24} className="text-white transform -rotate-12 transition-transform duration-500" />
                  </div>
                ) : (
                  <div className="animate-pulse flex items-center justify-center">
                    <Logo size={32} showText={false} />
                  </div>
                )}
              </div>
            </div>

            {/* Title & Status */}
            <h2 className="text-xl sm:text-2xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
              {generationStage === 4 ? "Workspace Ready!" : "Forging Your Workspace..."}
            </h2>
            <p className="text-xs sm:text-sm mt-1.5 max-w-xs sm:max-w-md mx-auto leading-relaxed px-2" style={{ color: "var(--txt-m)" }}>
              {generationStage === 4
                ? "Your environment is prepared. Redirecting in a few seconds..."
                : generationStatus}
            </p>

            {generationStage === 4 && (
              <div
                className="inline-flex items-center gap-2 px-3 sm:px-3.5 py-1 sm:py-1.5 mt-3 rounded-full border text-[11px] sm:text-xs font-semibold transition-all animate-fade-in max-w-full shadow-sm"
                style={{
                  background: "rgba(16, 185, 129, 0.1)",
                  borderColor: "rgba(16, 185, 129, 0.3)",
                  color: "#10b981",
                }}
              >
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping shrink-0" />
                <span className="truncate">Redirecting in a few seconds...</span>
              </div>
            )}

            {/* Progress Bar */}
            <div className="w-full max-w-md mt-6 space-y-2">
              <div
                className="w-full h-2 rounded-full overflow-hidden p-0.5 border"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div
                  className="h-full rounded-full transition-all duration-300 ease-out"
                  style={{
                    width: `${generationProgress}%`,
                    background: generationStage === 4
                      ? "#10b981"
                      : "linear-gradient(90deg, var(--accent), #ff7043, #10b981)",
                    boxShadow: "0 0 14px var(--glow)",
                  }}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono px-1" style={{ color: "var(--txt-m)" }}>
                <div className="flex items-center gap-2 font-bold" style={{ color: "var(--txt)" }}>
                  {/* Modern Animated Dataset Connector Badge */}
                  <div className="relative flex items-center justify-center">
                    {/* Subtle pulse aura */}
                    <span
                      className="absolute -inset-1 rounded-md opacity-35 animate-pulse pointer-events-none"
                      style={{ background: "var(--accent)" }}
                    />
                    {/* Authentic Connector / Dataset Logo */}
                    <div
                      className="relative flex items-center justify-center w-5 h-5 rounded-md border shadow-sm shrink-0 overflow-hidden"
                      style={{ background: "rgba(0,0,0,0.35)", borderColor: "var(--border)" }}
                    >
                      {selectedConnector?.Logo ? (
                        <selectedConnector.Logo size={14} className="shrink-0" />
                      ) : (
                        <Database size={13} style={{ color: "var(--accent)" }} />
                      )}
                    </div>
                    {/* Live processing activity indicator dot */}
                    {generationStage < 4 && (
                      <span className="absolute -top-0.5 -right-0.5 flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.9)]" />
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-bold tracking-tight">{selectedConnector.name}</span>
                </div>
                <span className="font-semibold text-emerald-400">{generationProgress}%</span>
              </div>
            </div>

            {/* 3 Live Stage Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 w-full max-w-lg mt-7">
              <div
                className="p-3 rounded-xl border flex items-center gap-2.5 text-left transition-all"
                style={{
                  background: generationStage >= 1 ? "rgba(16, 185, 129, 0.08)" : "var(--card)",
                  borderColor: generationStage >= 1 ? "rgba(16, 185, 129, 0.35)" : "var(--border)",
                }}
              >
                {generationStage > 1 ? (
                  <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                ) : (
                  <Loader2 size={16} className="animate-spin shrink-0" style={{ color: "var(--accent)" }} />
                )}
                <div className="min-w-0">
                  <p className="text-[11px] font-bold truncate" style={{ color: "var(--txt)" }}>1. Ingestion</p>
                  <p className="text-[9px] truncate" style={{ color: "var(--txt-m)" }}>
                    {generationStage > 1 ? "Data Loaded" : "Reading Stream"}
                  </p>
                </div>
              </div>

              <div
                className="p-3 rounded-xl border flex items-center gap-2.5 text-left transition-all"
                style={{
                  background: generationStage >= 2 ? "rgba(16, 185, 129, 0.08)" : "var(--card)",
                  borderColor: generationStage >= 2 ? "rgba(16, 185, 129, 0.35)" : "var(--border)",
                }}
              >
                {generationStage > 2 ? (
                  <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                ) : generationStage === 2 ? (
                  <Loader2 size={16} className="animate-spin shrink-0" style={{ color: "var(--accent)" }} />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-gray-600 shrink-0" />
                )}
                <div className="min-w-0">
                  <p className="text-[11px] font-bold truncate" style={{ color: "var(--txt)" }}>2. Profiling</p>
                  <p className="text-[9px] truncate" style={{ color: "var(--txt-m)" }}>
                    {generationStage > 2 ? "Schema Built" : generationStage === 2 ? "Analyzing..." : "Pending"}
                  </p>
                </div>
              </div>

              <div
                className="p-3 rounded-xl border flex items-center gap-2.5 text-left transition-all"
                style={{
                  background: generationStage >= 3 ? "rgba(16, 185, 129, 0.08)" : "var(--card)",
                  borderColor: generationStage >= 3 ? "rgba(16, 185, 129, 0.35)" : "var(--border)",
                }}
              >
                {generationStage >= 4 ? (
                  <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                ) : generationStage === 3 ? (
                  <Loader2 size={16} className="animate-spin shrink-0" style={{ color: "var(--accent)" }} />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-gray-600 shrink-0" />
                )}
                <div className="min-w-0">
                  <p className="text-[11px] font-bold truncate" style={{ color: "var(--txt)" }}>3. Studio</p>
                  <p className="text-[9px] truncate" style={{ color: "var(--txt-m)" }}>
                    {generationStage >= 4 ? "Ready" : generationStage === 3 ? "Mounting..." : "Pending"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* ── Two Column Layout ── */
          <div className="grid grid-cols-1 md:grid-cols-12 min-h-[440px]">
          {/* ── Left Column: Connectors (5 cols) ── */}
          <div
            className="md:col-span-5 border-b md:border-b-0 md:border-r p-4 space-y-3"
            style={{
              borderColor: "var(--border)",
              background: "var(--surface)",
            }}
          >
            {/* Header + Category dropdown */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                Sources
              </span>
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setIsCategoryDropdownOpen(!isCategoryDropdownOpen)}
                  className="px-2 py-0.5 rounded-md border text-[11px] flex items-center gap-1 transition-colors cursor-pointer"
                  style={{
                    background: "var(--card)",
                    borderColor: "var(--border)",
                    color: "var(--txt)",
                  }}
                >
                  <span className="capitalize">
                    {selectedCategory === "all" ? "All Sources" : selectedCategory}
                  </span>
                  <ChevronDown size={11} style={{ color: "var(--txt-m)" }} />
                </button>

                {isCategoryDropdownOpen && (
                  <div
                    className="absolute right-0 mt-1 w-36 rounded-xl border shadow-xl z-30 py-1 text-xs"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                    }}
                  >
                    {[
                      { id: "all", label: "All Sources" },
                      { id: "spreadsheets", label: "Cloud Sheets" },
                      { id: "warehouses", label: "Warehouses" },
                      { id: "relational", label: "SQL Databases" },
                      { id: "storage", label: "Cloud Storage" },
                      { id: "files", label: "Local Files" },
                    ].map((cat) => (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => {
                          setSelectedCategory(cat.id as any);
                          setIsCategoryDropdownOpen(false);
                        }}
                        className="w-full text-left px-3 py-1.5 transition-colors cursor-pointer"
                        style={{
                          color: selectedCategory === cat.id ? "var(--accent)" : "var(--txt)",
                          background: selectedCategory === cat.id ? "var(--glow)" : "transparent",
                          fontWeight: selectedCategory === cat.id ? 700 : 500,
                        }}
                      >
                        {cat.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Search Input */}
            <div className="relative">
              <Search
                size={12}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: "var(--txt-m)" }}
              />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search sources..."
                className="w-full rounded-lg py-1.5 pl-7 pr-2.5 text-xs focus:outline-none transition-colors border"
                style={{
                  background: "var(--inp-bg)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              />
            </div>

            {/* Categorized Connector Groups */}
            <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1 no-scrollbar">
              {/* Group 0: Cloud Spreadsheets */}
              {spreadsheets.length > 0 && (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-[11px] font-semibold" style={{ color: "var(--txt-m)" }}>
                    <span>Cloud Sheets</span>
                    <span className="text-[9px] font-mono opacity-70">Google / M365</span>
                  </div>
                  <div className="grid grid-cols-2 gap-1.5">
                    {spreadsheets.map((c) => {
                      const isSelected = selectedConnector.id === c.id;
                      const Logo = c.Logo;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => handleSelectConnector(c)}
                          className="p-2.5 rounded-xl border flex flex-col items-center justify-center gap-1 cursor-pointer transition-all duration-150"
                          style={{
                            background: isSelected ? "var(--glow)" : "var(--card)",
                            borderColor: isSelected ? "var(--accent)" : "var(--border)",
                            boxShadow: isSelected ? "0 0 12px var(--glow)" : "none",
                            color: isSelected ? "var(--txt)" : "var(--txt-m)",
                            fontWeight: isSelected ? 700 : 500,
                          }}
                        >
                          <Logo size={22} />
                          <span className="text-[11px] truncate w-full text-center font-semibold">{c.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Group 1: Warehouses */}
              {warehouses.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold" style={{ color: "var(--txt-m)" }}>
                    Warehouses
                  </div>
                  <div className="grid grid-cols-3 gap-1.5">
                    {warehouses.map((c) => {
                      const isSelected = selectedConnector.id === c.id;
                      const Logo = c.Logo;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => handleSelectConnector(c)}
                          className="p-2.5 rounded-xl border flex flex-col items-center justify-center gap-1 cursor-pointer transition-all duration-150"
                          style={{
                            background: isSelected ? "var(--glow)" : "var(--card)",
                            borderColor: isSelected ? "var(--accent)" : "var(--border)",
                            boxShadow: isSelected ? "0 0 12px var(--glow)" : "none",
                            color: isSelected ? "var(--txt)" : "var(--txt-m)",
                          }}
                        >
                          <Logo size={20} />
                          <span className="text-[10px] truncate w-full text-center font-medium">{c.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Group 2: Relational DBs */}
              {relationalDbs.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold" style={{ color: "var(--txt-m)" }}>
                    SQL Databases
                  </div>
                  <div className="grid grid-cols-3 gap-1.5">
                    {relationalDbs.map((c) => {
                      const isSelected = selectedConnector.id === c.id;
                      const Logo = c.Logo;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => handleSelectConnector(c)}
                          className="p-2.5 rounded-xl border flex flex-col items-center justify-center gap-1 cursor-pointer transition-all duration-150"
                          style={{
                            background: isSelected ? "var(--glow)" : "var(--card)",
                            borderColor: isSelected ? "var(--accent)" : "var(--border)",
                            boxShadow: isSelected ? "0 0 12px var(--glow)" : "none",
                            color: isSelected ? "var(--txt)" : "var(--txt-m)",
                          }}
                        >
                          <Logo size={20} />
                          <span className="text-[10px] truncate w-full text-center font-medium">{c.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Group 3: Storage */}
              {cloudStorage.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold" style={{ color: "var(--txt-m)" }}>
                    Cloud Storage
                  </div>
                  <div className="grid grid-cols-3 gap-1.5">
                    {cloudStorage.map((c) => {
                      const isSelected = selectedConnector.id === c.id;
                      const Logo = c.Logo;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => handleSelectConnector(c)}
                          className="p-2.5 rounded-xl border flex flex-col items-center justify-center gap-1 cursor-pointer transition-all duration-150"
                          style={{
                            background: isSelected ? "var(--glow)" : "var(--card)",
                            borderColor: isSelected ? "var(--accent)" : "var(--border)",
                            boxShadow: isSelected ? "0 0 12px var(--glow)" : "none",
                            color: isSelected ? "var(--txt)" : "var(--txt-m)",
                          }}
                        >
                          <Logo size={20} />
                          <span className="text-[10px] truncate w-full text-center font-medium">{c.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Group 4: Local Files */}
              {localFiles.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold" style={{ color: "var(--txt-m)" }}>
                    Local Files
                  </div>
                  <div className="grid grid-cols-4 gap-1.5">
                    {localFiles.map((c) => {
                      const isSelected = selectedConnector.id === c.id;
                      const Logo = c.Logo;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => handleSelectConnector(c)}
                          className="p-2 rounded-xl border flex flex-col items-center justify-center gap-1 cursor-pointer transition-all duration-150"
                          style={{
                            background: isSelected ? "var(--glow)" : "var(--card)",
                            borderColor: isSelected ? "var(--accent)" : "var(--border)",
                            boxShadow: isSelected ? "0 0 12px var(--glow)" : "none",
                            color: isSelected ? "var(--txt)" : "var(--txt-m)",
                          }}
                        >
                          <Logo size={18} />
                          <span className="text-[10px] truncate w-full text-center font-medium">{c.name}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ── Right Column: Configuration & Launch (7 cols) ── */}
          <div
            className="md:col-span-7 p-5 flex flex-col justify-between space-y-4"
            style={{
              background: "var(--bg)",
            }}
          >
            <div>
              {/* Active Connector Banner */}
              <div className="flex items-center justify-between pb-3 border-b mb-3.5" style={{ borderColor: "var(--border)" }}>
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border"
                    style={{
                      background: "var(--glow)",
                      borderColor: "var(--accent)",
                      color: "var(--accent)",
                    }}
                  >
                    <selectedConnector.Logo size={18} />
                  </div>
                  <div>
                    <h5 className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                      {selectedConnector.name}
                    </h5>
                    <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                      {selectedConnector.subtitle}
                    </p>
                  </div>
                </div>
              </div>

              {/* Form Content */}
              {selectedConnector.category === "spreadsheets" ? (
                /* Online Spreadsheets Panel */
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="block text-[11px] font-semibold" style={{ color: "var(--txt)" }}>
                      {selectedConnector.id === "google_sheets"
                        ? "Google Sheets Public Link"
                        : "OneDrive / SharePoint Link"}
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="url"
                        value={connUri}
                        onChange={(e) => setConnUri(e.target.value)}
                        placeholder={selectedConnector.defaultUri}
                        className="flex-1 border rounded-xl px-3 py-2 text-xs font-mono focus:outline-none transition-colors"
                        style={{
                          background: "var(--inp-bg)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      />
                      {(selectedConnector.id === "google_sheets" || selectedConnector.id === "excel_online") && (
                        <button
                          type="button"
                          onClick={() => handleDetectSheetTabs()}
                          disabled={isDetectingTabs || !connUri.trim()}
                          className="px-2.5 py-2 rounded-xl border text-xs font-medium flex items-center gap-1.5 transition-all shrink-0 cursor-pointer disabled:opacity-40 hover:border-orange-500/50"
                          style={{
                            background: "var(--surface)",
                            borderColor: "var(--border)",
                            color: "var(--txt)",
                          }}
                          title={
                            selectedConnector.id === "google_sheets"
                              ? "Scan Google Sheet for worksheet tabs"
                              : "Scan Microsoft 365 / OneDrive workbook for worksheet tabs"
                          }
                        >
                          {isDetectingTabs ? (
                            <Loader2 size={12} className="animate-spin" style={{ color: "var(--accent)" }} />
                          ) : (
                            <Search size={12} style={{ color: "var(--accent)" }} />
                          )}
                          <span>Tabs</span>
                        </button>
                      )}
                    </div>
                    <p className="text-[10px] pt-0.5" style={{ color: "var(--txt-m)" }}>
                      {selectedConnector.id === "google_sheets"
                        ? "Ensure document is set to 'Anyone with the link can view'."
                        : "Supports 1drv.ms, onedrive.live.com, or sharepoint.com public view links."}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="block text-[11px] font-semibold" style={{ color: "var(--txt)" }}>
                        Tab / Sheet Name <span className="opacity-60 font-normal">(Optional)</span>
                      </label>
                      {sheetTabs.length > 0 && (
                        <span className="text-[10px] font-mono font-semibold" style={{ color: "var(--accent)" }}>
                          {sheetTabs.length} tabs found
                        </span>
                      )}
                    </div>
                    {sheetTabs.length > 0 ? (
                      <select
                        value={targetTable}
                        onChange={(e) => setTargetTable(e.target.value)}
                        className="w-full border rounded-xl px-3 py-2 text-xs font-mono focus:outline-none cursor-pointer"
                        style={{
                          background: "var(--inp-bg)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      >
                        {sheetTabs.map((tab) => (
                          <option key={tab} value={tab}>
                            {tab}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={targetTable}
                        onChange={(e) => setTargetTable(e.target.value)}
                        placeholder="Sheet1"
                        className="w-full border rounded-xl px-3 py-1.5 text-xs font-mono focus:outline-none transition-colors"
                        style={{
                          background: "var(--inp-bg)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      />
                    )}
                  </div>

                  {/* Quick Demo Pre-fill */}
                  <div className="pt-1 flex items-center gap-2 text-[11px]">
                    <span style={{ color: "var(--txt-m)" }}>Try sample:</span>
                    {selectedConnector.id === "google_sheets" ? (
                      <button
                        type="button"
                        onClick={() => {
                          setConnUri("https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit");
                          setTargetTable("Sheet1");
                        }}
                        className="text-[10px] font-semibold underline cursor-pointer"
                        style={{ color: "var(--accent)" }}
                      >
                        Public Demo Sheet
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => {
                          setConnUri("https://onedrive.live.com/download?cid=DEMO&resid=DEMO%21123&authkey=DEMO");
                          setTargetTable("Sheet1");
                        }}
                        className="text-[10px] font-semibold underline cursor-pointer"
                        style={{ color: "var(--accent)" }}
                      >
                        Public Demo Workbook
                      </button>
                    )}
                  </div>
                </div>
              ) : selectedConnector.category === "files" ? (
                /* Local File Drag & Drop */
                <div className="space-y-2.5">
                  <div
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className="border border-dashed rounded-xl p-4 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-1.5"
                    style={{
                      background: isDragging ? "var(--glow)" : "var(--inp-bg)",
                      borderColor: isDragging ? "var(--accent)" : "var(--border)",
                    }}
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={(e) => {
                        if (e.target.files?.[0]) handleIncomingFile(e.target.files[0]);
                      }}
                      accept={getExpectedExtensions(selectedConnector.id).accept}
                      className="hidden"
                    />
                    <UploadCloud size={22} style={{ color: "var(--accent)" }} />
                    {selectedFile ? (
                      <div>
                        <p className="text-xs font-bold flex items-center justify-center gap-1" style={{ color: "var(--accent)" }}>
                          <CheckCircle2 size={12} /> {selectedFile.name}
                        </p>
                        <p className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                          {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {getExpectedExtensions(selectedConnector.id).label} Verified
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-xs font-medium" style={{ color: "var(--txt)" }}>
                          Drop {getExpectedExtensions(selectedConnector.id).label} file here or click to browse
                        </p>
                        <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                          {getExpectedExtensions(selectedConnector.id).hint}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Sample datasets */}
                  <div className="flex items-center gap-1.5 pt-1 overflow-x-auto no-scrollbar">
                    <span className="text-[10px] shrink-0" style={{ color: "var(--txt-m)" }}>Sample:</span>
                    {SAMPLE_DATASETS.slice(0, 3).map((sample) => (
                      <button
                        key={sample.id}
                        type="button"
                        onClick={() => handleQuickSample(sample)}
                        className="px-2 py-0.5 rounded-md border text-[10px] shrink-0 cursor-pointer transition-colors"
                        style={{
                          background: "var(--surface)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      >
                        {sample.name}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Database / Warehouse / Storage */
                <div className="space-y-3">
                  <div>
                    <label className="block text-[11px] font-semibold mb-1" style={{ color: "var(--txt)" }}>
                      Connection URI
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={connUri}
                        onChange={(e) => setConnUri(e.target.value)}
                        placeholder={selectedConnector.defaultUri}
                        className="flex-1 border rounded-xl px-3 py-2 text-xs font-mono focus:outline-none transition-colors"
                        style={{
                          background: "var(--inp-bg)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      />
                      <button
                        type="button"
                        onClick={handleTestPing}
                        disabled={isTesting}
                        className="px-3 py-2 rounded-xl border text-xs font-medium flex items-center gap-1.5 transition-all shrink-0 cursor-pointer disabled:opacity-50"
                        style={{
                          background: "var(--surface)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      >
                        {isTesting ? (
                          <Loader2 size={12} className="animate-spin" style={{ color: "var(--accent)" }} />
                        ) : (
                          <Zap size={12} style={{ color: "var(--accent)" }} />
                        )}
                        <span>Ping</span>
                      </button>
                    </div>

                    <p className="text-[10px] pt-1" style={{ color: "var(--txt-m)" }}>
                      Supports cloud services (AWS RDS, PlanetScale, Supabase, ClickHouse Cloud) and local database instances (127.0.0.1).
                    </p>

                    {testResult && (
                      <div
                        className="text-[10px] font-mono mt-1.5 p-2 rounded-lg border flex items-start gap-1.5 leading-snug"
                        style={{
                          background: testResult.ok ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
                          borderColor: testResult.ok ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)",
                          color: testResult.ok ? "#34d399" : "#fca5a5",
                        }}
                      >
                        {testResult.ok ? (
                          <CheckCircle2 size={12} className="shrink-0 text-emerald-400 mt-0.5" />
                        ) : (
                          <AlertCircle size={12} className="shrink-0 text-red-400 mt-0.5" />
                        )}
                        <span className="flex-1 break-words">{testResult.message}</span>
                      </div>
                    )}
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold mb-1" style={{ color: "var(--txt)" }}>
                      Target Table
                    </label>
                    {dbTables.length > 0 ? (
                      <select
                        value={targetTable}
                        onChange={(e) => setTargetTable(e.target.value)}
                        className="w-full border rounded-xl px-3 py-1.5 text-xs font-mono focus:outline-none"
                        style={{
                          background: "var(--inp-bg)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      >
                        {dbTables.map((t) => (
                          <option key={t} value={t}>
                            {t}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={targetTable}
                        onChange={(e) => setTargetTable(e.target.value)}
                        placeholder="public.users"
                        className="w-full border rounded-xl px-3 py-1.5 text-xs font-mono focus:outline-none transition-colors"
                        style={{
                          background: "var(--inp-bg)",
                          borderColor: "var(--border)",
                          color: "var(--txt)",
                        }}
                      />
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Error Message & Launch Button */}
            <div className="pt-3 border-t flex items-center justify-between gap-3" style={{ borderColor: "var(--border)" }}>
              <div className="min-w-0 flex-1">
                {errorMsg && (
                  <p className="text-xs text-rose-500 truncate flex items-center gap-1.5 font-medium">
                    <AlertCircle size={13} className="shrink-0" />
                    <span>{errorMsg}</span>
                  </p>
                )}
              </div>

              <button
                type="button"
                onClick={handleConnect}
                disabled={isConnecting}
                className="px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm transition-all flex items-center gap-2 cursor-pointer shrink-0 disabled:opacity-50 hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  background: "var(--accent)",
                  color: "#ffffff",
                  boxShadow: "0 0 20px var(--glow)",
                }}
              >
                {isConnecting ? (
                  <>
                    <Loader2 size={13} className="animate-spin" />
                    <span>Generating Workspace...</span>
                  </>
                ) : (
                  <>
                    <span>Generate Workspace</span>
                    <ArrowRight size={13} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
}
