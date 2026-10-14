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
    defaultUri: "mysql+pymysql://root:***@localhost:3306/production",
    targetTable: "orders",
    Logo: MySQLLogo,
  },
  {
    id: "clickhouse",
    name: "ClickHouse",
    category: "relational",
    subtitle: "Columnar OLAP",
    defaultUri: "clickhouse+native://default:***@localhost:9000/default",
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

function validateConnectorInput(
  connectorId: string,
  category: ConnectorCategory,
  uri: string,
  file: File | null
): { valid: boolean; error?: string } {
  if (category === "files") {
    if (!file) {
      return { valid: false, error: "Please select or drop a dataset file (.csv, .xlsx, .parquet, or .json) to upload." };
    }
    const ext = file.name.split(".").pop()?.toLowerCase();
    const allowed = ["csv", "xlsx", "xls", "parquet", "json"];
    if (!ext || !allowed.includes(ext)) {
      return {
        valid: false,
        error: `Unsupported file extension (.${ext}). Supported: CSV, Excel, Parquet, JSON.`,
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

  // File Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Ingestion / Launching State
  const [isConnecting, setIsConnecting] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  React.useEffect(() => {
    if (isOpen && initialConnectorId) {
      const match = ALL_CONNECTORS.find((c) => c.id === initialConnectorId);
      if (match) {
        setSelectedConnector(match);
        setConnUri("");
        setTargetTable("");
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
      setTestResult({
        ok: data.ok,
        message: data.message || (data.ok ? "Connected" : "Failed"),
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
    setErrorMsg("");

    try {
      let uploadId = "";
      const cleanUri = sanitizeInput(connUri);
      const cleanTable = sanitizeInput(targetTable);

      if (selectedConnector.category === "spreadsheets") {
        if (selectedConnector.id === "google_sheets") {
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

        const formData = new FormData();
        formData.append("file", selectedFile);
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

      // Default role is Admin
      if (typeof window !== "undefined") {
        localStorage.setItem("df_user_role", "Admin");
      }

      onClose();
      router.push(`/workspace?upload_id=${uploadId}`);
    } catch (err: any) {
      setErrorMsg(err.message || "Connection failed");
    } finally {
      setIsConnecting(false);
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
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleQuickSample = (sample: SampleDataset) => {
    const blob = new Blob([sample.csvContent], { type: "text/csv" });
    const file = new File([blob], sample.filename, { type: "text/csv" });
    setSelectedFile(file);
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-5 backdrop-blur-md animate-fadeIn"
      style={{ background: "rgba(0, 0, 0, 0.72)" }}
      onClick={onClose}
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
                color: "var(--accent)",
              }}
            >
              <Zap size={16} />
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight" style={{ color: "var(--txt)" }}>
                Ingestion Hub
              </h3>
              <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>
                Connect your data source or upload a dataset to launch your workspace.
              </p>
            </div>
          </div>

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
        </div>

        {/* ── Two Column Layout ── */}
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
                    {selectedConnector.id === "postgresql" ? (
                      <Zap size={16} />
                    ) : (
                      <selectedConnector.Logo size={18} />
                    )}
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
                    <input
                      type="url"
                      value={connUri}
                      onChange={(e) => setConnUri(e.target.value)}
                      placeholder={selectedConnector.defaultUri}
                      className="w-full border rounded-xl px-3 py-2 text-xs font-mono focus:outline-none transition-colors"
                      style={{
                        background: "var(--inp-bg)",
                        borderColor: "var(--border)",
                        color: "var(--txt)",
                      }}
                    />
                    <p className="text-[10px] pt-0.5" style={{ color: "var(--txt-m)" }}>
                      {selectedConnector.id === "google_sheets"
                        ? "Ensure document is set to 'Anyone with the link can view'."
                        : "Supports 1drv.ms, onedrive.live.com, or sharepoint.com public view links."}
                    </p>
                  </div>

                  <div className="space-y-1">
                    <label className="block text-[11px] font-semibold" style={{ color: "var(--txt)" }}>
                      Tab / Sheet Name <span className="opacity-60 font-normal">(Optional)</span>
                    </label>
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
                        if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
                      }}
                      accept=".csv,.xlsx,.xls,.parquet,.json"
                      className="hidden"
                    />
                    <UploadCloud size={22} style={{ color: "var(--accent)" }} />
                    {selectedFile ? (
                      <div>
                        <p className="text-xs font-bold flex items-center justify-center gap-1" style={{ color: "var(--accent)" }}>
                          <CheckCircle2 size={12} /> {selectedFile.name}
                        </p>
                        <p className="text-[10px] font-mono" style={{ color: "var(--txt-m)" }}>
                          {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                        </p>
                      </div>
                    ) : (
                      <div>
                        <p className="text-xs font-medium" style={{ color: "var(--txt)" }}>
                          Drop file here or click to browse
                        </p>
                        <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                          Supports CSV, Excel (.xlsx), Parquet, JSON (max 100MB)
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

                    {testResult && (
                      <p
                        className="text-[10px] font-mono mt-1 flex items-center gap-1"
                        style={{
                          color: testResult.ok ? "var(--accent)" : "#ef4444",
                        }}
                      >
                        {testResult.ok ? <CheckCircle2 size={11} /> : <AlertCircle size={11} />}
                        {testResult.message}
                      </p>
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
      </div>
    </div>
  );
}
