"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import {
  PostgresLogo,
  MySQLLogo,
  ClickHouseLogo,
  CSVLogo,
  ExcelLogo,
  ParquetLogo,
  JSONLogo,
  GoogleSheetsLogo,
  MicrosoftExcelOnlineLogo,
} from "./DataLogos";
import { SAMPLE_DATASETS, SampleDataset } from "./sampleDatasets";
import {
  Search,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  UploadCloud,
} from "lucide-react";

interface WorkspaceLaunchModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: string;
  initialConnectorId?: string;
  hasActiveDataset?: boolean;
  activeDatasetName?: string;
}

export type ConnectorCategory = "files" | "spreadsheets" | "relational" | "samples";

interface ConnectorDef {
  id: string;
  name: string;
  category: "files" | "spreadsheets" | "relational";
  subtitle: string;
  tag: string;
  defaultUri: string;
  targetTable: string;
  Logo: React.ComponentType<{ size?: number; className?: string }>;
}

const ALL_CONNECTORS: ConnectorDef[] = [
  // Local Files (Primary front door)
  {
    id: "csv",
    name: "CSV",
    category: "files",
    subtitle: "Comma-Separated Values (.csv)",
    tag: "Instant Parse",
    defaultUri: "dataset.csv",
    targetTable: "dataset.csv",
    Logo: CSVLogo,
  },
  {
    id: "excel",
    name: "Excel",
    category: "files",
    subtitle: "Microsoft Excel Workbook (.xlsx, .xls)",
    tag: "Spreadsheet",
    defaultUri: "report.xlsx",
    targetTable: "Sheet1",
    Logo: ExcelLogo,
  },
  {
    id: "parquet",
    name: "Parquet",
    category: "files",
    subtitle: "Apache Parquet Columnar (.parquet)",
    tag: "High Perf",
    defaultUri: "events.parquet",
    targetTable: "events.parquet",
    Logo: ParquetLogo,
  },
  {
    id: "json",
    name: "JSON",
    category: "files",
    subtitle: "JSON Records & Lines (.json, .jsonl)",
    tag: "Structured",
    defaultUri: "records.json",
    targetTable: "records.json",
    Logo: JSONLogo,
  },

  // Online Spreadsheets & Cloud Links
  {
    id: "google_sheets",
    name: "Google Sheets",
    category: "spreadsheets",
    subtitle: "Public / Shared Live Link",
    tag: "Live Sync",
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

  // Relational SQL Databases
  {
    id: "postgresql",
    name: "PostgreSQL",
    category: "relational",
    subtitle: "PostgreSQL / Supabase / Neon",
    tag: "v12-16",
    defaultUri: "postgresql://postgres:***@db.project-ref.supabase.co:5432/postgres",
    targetTable: "public.users",
    Logo: PostgresLogo,
  },
  {
    id: "mysql",
    name: "MySQL",
    category: "relational",
    subtitle: "MySQL / AWS RDS / PlanetScale",
    tag: "v8.0+",
    defaultUri: "mysql+pymysql://admin:***@mysql.us-east-1.rds.amazonaws.com:3306/production",
    targetTable: "orders",
    Logo: MySQLLogo,
  },
  {
    id: "clickhouse",
    name: "ClickHouse",
    category: "relational",
    subtitle: "ClickHouse Cloud / OLAP Engine",
    tag: "Columnar DB",
    defaultUri: "clickhouse+native://default:***@service.us-east-1.clickhouse.cloud:9440/default",
    targetTable: "telemetry_logs",
    Logo: ClickHouseLogo,
  },
];

/* ── Input Sanitizer & Validator ── */
function sanitizeInput(raw: string): string {
  if (!raw) return "";
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
        hint: "Supports standard CSV datasets with headers (.csv, max 100MB)",
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
        hint: "Supports Apache Parquet columnar binary datasets (.parquet, max 100MB)",
      };
    case "json":
      return {
        label: "JSON",
        extensions: ["json", "jsonl", "ndjson"],
        accept: ".json,.jsonl,.ndjson",
        hint: "Supports JSON records, arrays, or newline-delimited JSON (.json, max 100MB)",
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
      return { valid: false, error: "File exceeds 100MB limit. For large tables, connect directly via a SQL Database." };
    }
    return { valid: true };
  }

  if (category === "samples") {
    if (!file) {
      return { valid: false, error: "Please select one of the demo benchmark datasets." };
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

  if (category === "relational") {
    if (!clean.includes("://")) {
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
  hasActiveDataset = false,
  activeDatasetName = "",
}: WorkspaceLaunchModalProps) {
  const router = useRouter();

  // Selected Connector (defaults to initialConnectorId, csv or postgresql)
  const [selectedConnector, setSelectedConnector] = useState<ConnectorDef>(() => {
    if (initialConnectorId) {
      const match = ALL_CONNECTORS.find((c) => c.id === initialConnectorId);
      if (match) return match;
    }
    return ALL_CONNECTORS.find((c) => c.id === "csv") || ALL_CONNECTORS[0];
  });

  // Search & Category Filter
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<"all" | ConnectorCategory>("all");

  // Connection inputs
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

  useEffect(() => {
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
        }, 600);
        return () => clearTimeout(timer);
      }
    }
  }, [connUri, selectedConnector.id]);

  useEffect(() => {
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
  useEffect(() => {
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
      c.subtitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.tag.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === "all" || c.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const localFiles = ALL_CONNECTORS.filter((c) => c.category === "files");
  const spreadsheets = ALL_CONNECTORS.filter((c) => c.category === "spreadsheets");
  const relationalDbs = ALL_CONNECTORS.filter((c) => c.category === "relational");

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

      if (selectedCategory === "samples" && selectedFile) {
        setGenerationStatus(`Ingesting demo dataset: ${selectedFile.name}...`);
        const formData = new FormData();
        formData.append("file", selectedFile);
        formData.append("expected_format", "csv");
        const res = await apiFetch("/upload", {
          method: "POST",
          body: formData,
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Upload failed" }));
          throw new Error(err.detail || "Demo dataset upload failed.");
        }
        const data = await res.json();
        uploadId = data.upload_id;
      } else if (selectedConnector.category === "spreadsheets") {
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
        // Relational SQL Database
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

      setTimeout(() => {
        onClose();
        router.push(`/workspace?upload_id=${uploadId}`);
      }, 1200);
    } catch (err: any) {
      setIsGeneratingWorkspace(false);
      setIsConnecting(false);
      setErrorMsg(err.message || "Failed to launch workspace. Check connection settings.");
    }
  };

  const handleConnect = async () => {
    if (hasActiveDataset) {
      setErrorMsg(`A dataset ('${activeDatasetName || "Dataset"}') is already active in your workspace. You cannot upload any other dataset.`);
      return;
    }

    const val = validateConnectorInput(
      selectedConnector.id,
      selectedCategory === "samples" ? "samples" : selectedConnector.category,
      connUri,
      selectedFile
    );
    if (!val.valid) {
      setErrorMsg(val.error || "Invalid input");
      return;
    }
    setErrorMsg("");
    await executeIngestion();
  };

  const handleIncomingFile = (file: File) => {
    if (hasActiveDataset) {
      setErrorMsg(`A dataset ('${activeDatasetName || "Dataset"}') is already active in your workspace. You cannot upload any other dataset.`);
      return;
    }
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
      setErrorMsg("File exceeds 100MB limit. For large tables, connect directly via a SQL Database.");
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
    if (hasActiveDataset) {
      setErrorMsg(`A dataset ('${activeDatasetName || "Dataset"}') is already active in your workspace. You cannot upload any other dataset.`);
      return;
    }
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleIncomingFile(e.dataTransfer.files[0]);
    }
  };

  const handleQuickSample = (sample: SampleDataset) => {
    if (hasActiveDataset) {
      setErrorMsg(`A dataset ('${activeDatasetName || "Dataset"}') is already active in your workspace. You cannot upload any other dataset.`);
      return;
    }
    const csvConnector = ALL_CONNECTORS.find((c) => c.id === "csv") || selectedConnector;
    setSelectedConnector(csvConnector);
    const blob = new Blob([sample.csvContent], { type: "text/csv" });
    const file = new File([blob], sample.filename, { type: "text/csv" });
    setSelectedFile(file);
    setErrorMsg("");
  };

  const handleLaunchSampleDirect = async (sample: SampleDataset) => {
    if (hasActiveDataset) {
      setErrorMsg(`A dataset ('${activeDatasetName || "Dataset"}') is already active in your workspace. You cannot upload any other dataset.`);
      return;
    }
    const csvConnector = ALL_CONNECTORS.find((c) => c.id === "csv") || selectedConnector;
    setSelectedConnector(csvConnector);
    const blob = new Blob([sample.csvContent], { type: "text/csv" });
    const file = new File([blob], sample.filename, { type: "text/csv" });
    setSelectedFile(file);
    setErrorMsg("");

    setIsConnecting(true);
    setIsGeneratingWorkspace(true);
    setGenerationStage(1);
    setGenerationProgress(25);
    setGenerationStatus(`Loading demo benchmark: ${sample.name}...`);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("expected_format", "csv");
      const res = await apiFetch("/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Demo dataset upload failed.");
      }
      const data = await res.json();
      const uploadId = data.upload_id;

      setGenerationStage(4);
      setGenerationProgress(100);
      setGenerationStatus("Dataset ready! Launching workspace...");

      if (typeof window !== "undefined") {
        localStorage.setItem("df_user_role", "Admin");
        localStorage.setItem("df_last_upload_id", uploadId);
      }

      setTimeout(() => {
        onClose();
        router.push(`/workspace?upload_id=${uploadId}`);
      }, 1000);
    } catch (err: any) {
      setIsGeneratingWorkspace(false);
      setIsConnecting(false);
      setErrorMsg(err.message || "Failed to launch demo dataset.");
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 backdrop-blur-sm animate-fadeIn"
      style={{ background: "rgba(0, 0, 0, 0.7)" }}
      onClick={isGeneratingWorkspace ? undefined : onClose}
    >
      <div
        className="w-full max-w-3xl rounded-xl shadow-2xl overflow-hidden flex flex-col relative animate-slideUp text-[var(--txt)]"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-6 py-4 border-b flex items-center justify-between shrink-0"
          style={{ borderColor: "var(--border)" }}
        >
          <div>
            <h3 className="text-sm font-semibold tracking-tight">
              {isGeneratingWorkspace ? "Opening Workspace" : "Import Data"}
            </h3>
            <p className="text-xs text-[var(--txt-m)] mt-0.5">
              {isGeneratingWorkspace
                ? "Setting up your data session..."
                : "Select a source to load into your workspace"}
            </p>
          </div>

          {!isGeneratingWorkspace && (
            <button
              onClick={onClose}
              className="text-[var(--txt-m)] hover:text-[var(--txt)] p-1 rounded-md transition-colors cursor-pointer"
              aria-label="Close"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Loading Overlay */}
        {isGeneratingWorkspace ? (
          <div className="p-12 min-h-[360px] flex flex-col items-center justify-center text-center">
            <Loader2 size={26} className="animate-spin text-indigo-500 mb-4" />
            <h4 className="text-sm font-semibold">
              {generationStage === 4 ? "Workspace Ready" : "Loading Dataset"}
            </h4>
            <p className="text-xs text-[var(--txt-m)] mt-1 max-w-sm">
              {generationStage === 4 ? "Redirecting to workspace..." : generationStatus}
            </p>
          </div>
        ) : (
          <>
            {hasActiveDataset && (
              <div
                className="mx-6 mt-4 p-3 rounded-lg border text-xs flex items-start gap-2.5"
                style={{
                  background: "rgba(239, 68, 68, 0.08)",
                  borderColor: "rgba(239, 68, 68, 0.25)",
                }}
              >
                <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <span className="font-medium text-red-400">Dataset already active: </span>
                  <span className="text-[var(--txt-m)]">
                    &apos;{activeDatasetName || "Dataset"}&apos; is already open. Close it before importing another.
                  </span>
                </div>
              </div>
            )}

            {/* Category Navigation (Minimal text tabs - no pills) */}
            <div
              className="px-6 border-b flex items-center gap-6 text-xs"
              style={{ borderColor: "var(--border)" }}
            >
              {[
                { id: "all", label: "All" },
                { id: "files", label: "Files" },
                { id: "spreadsheets", label: "Cloud Sheets" },
                { id: "relational", label: "Databases" },
                { id: "samples", label: "Sample Data" },
              ].map((cat) => {
                const isActive = selectedCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedCategory(cat.id as any)}
                    className={`py-3 font-medium transition-colors border-b-2 -mb-px cursor-pointer ${
                      isActive
                        ? "border-indigo-500 text-[var(--txt)]"
                        : "border-transparent text-[var(--txt-m)] hover:text-[var(--txt)]"
                    }`}
                  >
                    {cat.label}
                  </button>
                );
              })}
            </div>

            {/* Main Content Area */}
            <div className="grid grid-cols-1 md:grid-cols-12 min-h-[380px]">
              {/* Left Column: Source Selection (5 cols) */}
              <div
                className="md:col-span-5 border-b md:border-b-0 md:border-r p-4 flex flex-col gap-3"
                style={{ borderColor: "var(--border)" }}
              >
                {/* Search */}
                <div className="relative">
                  <Search
                    size={13}
                    className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--txt-f)] pointer-events-none"
                  />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search sources..."
                    className="w-full rounded-md py-1.5 pl-8 pr-2.5 text-xs bg-[var(--bg)] border border-[var(--border)] text-[var(--txt)] focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {/* List */}
                <div className="flex-1 overflow-y-auto space-y-1 pr-1 max-h-[320px]">
                  {selectedCategory === "samples" ? (
                    SAMPLE_DATASETS.map((sample) => (
                      <button
                        key={sample.id}
                        type="button"
                        onClick={() => handleLaunchSampleDirect(sample)}
                        className="w-full text-left p-2.5 rounded-lg border border-[var(--border)] hover:border-indigo-500/50 bg-[var(--card)] hover:bg-[var(--surface)] transition-all cursor-pointer"
                      >
                        <div className="flex items-center justify-between text-xs font-medium">
                          <span>{sample.name}</span>
                          <span className="text-[10px] text-[var(--txt-f)] font-mono">
                            {sample.rows} × {sample.cols}
                          </span>
                        </div>
                        <p className="text-[11px] text-[var(--txt-m)] line-clamp-1 mt-0.5">
                          {sample.description}
                        </p>
                      </button>
                    ))
                  ) : (
                    filteredConnectors.map((c) => {
                      const isSelected = selectedConnector.id === c.id;
                      const Logo = c.Logo;
                      return (
                        <button
                          key={c.id}
                          type="button"
                          onClick={() => handleSelectConnector(c)}
                          className={`w-full flex items-center gap-3 p-2.5 rounded-lg text-left transition-colors border cursor-pointer ${
                            isSelected
                              ? "bg-[var(--card)] border-indigo-500/60 text-[var(--txt)] font-medium"
                              : "border-transparent hover:bg-[var(--card)]/60 text-[var(--txt-m)] hover:text-[var(--txt)]"
                          }`}
                        >
                          <Logo size={18} />
                          <div className="min-w-0 flex-1">
                            <div className="text-xs font-medium leading-none">{c.name}</div>
                            <div className="text-[11px] text-[var(--txt-f)] truncate mt-1 leading-none">
                              {c.subtitle}
                            </div>
                          </div>
                        </button>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Right Column: Configuration & Actions (7 cols) */}
              <div className="md:col-span-7 p-6 flex flex-col justify-between">
                <div>
                  {/* Selected Source Header */}
                  <div className="flex items-center gap-2.5 pb-4 border-b mb-5" style={{ borderColor: "var(--border)" }}>
                    <selectedConnector.Logo size={20} />
                    <div>
                      <h4 className="text-xs font-semibold">{selectedConnector.name}</h4>
                      <p className="text-[11px] text-[var(--txt-m)]">{selectedConnector.subtitle}</p>
                    </div>
                  </div>

                  {/* Body according to connector type */}
                  {selectedConnector.category === "spreadsheets" ? (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-medium mb-1.5">
                          {selectedConnector.id === "google_sheets"
                            ? "Google Sheets URL"
                            : "Excel Online / OneDrive URL"}
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="url"
                            value={connUri}
                            onChange={(e) => setConnUri(e.target.value)}
                            placeholder={selectedConnector.defaultUri}
                            className="flex-1 rounded-md px-3 py-2 text-xs font-mono bg-[var(--bg)] border border-[var(--border)] text-[var(--txt)] focus:outline-none focus:border-indigo-500"
                          />
                          <button
                            type="button"
                            onClick={() => handleDetectSheetTabs()}
                            disabled={isDetectingTabs || !connUri.trim()}
                            className="px-3 py-2 rounded-md border border-[var(--border)] text-xs font-medium hover:bg-[var(--card)] disabled:opacity-40 transition-colors cursor-pointer"
                          >
                            {isDetectingTabs ? "Scanning..." : "Scan Tabs"}
                          </button>
                        </div>
                        <p className="text-[11px] text-[var(--txt-f)] mt-1.5">
                          Document must be accessible to anyone with the link.
                        </p>
                      </div>

                      {sheetTabs.length > 0 && (
                        <div>
                          <label className="block text-xs font-medium mb-1.5">Worksheet</label>
                          <select
                            value={targetTable}
                            onChange={(e) => setTargetTable(e.target.value)}
                            className="w-full rounded-md px-3 py-2 text-xs bg-[var(--bg)] border border-[var(--border)] text-[var(--txt)] focus:outline-none cursor-pointer"
                          >
                            {sheetTabs.map((t) => (
                              <option key={t} value={t}>
                                {t}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      <div className="text-[11px] text-[var(--txt-f)]">
                        Sample link:{" "}
                        <button
                          type="button"
                          onClick={() => {
                            setConnUri("https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit");
                            setTargetTable("Sheet1");
                          }}
                          className="text-indigo-400 hover:underline cursor-pointer"
                        >
                          Financial Sample
                        </button>
                      </div>
                    </div>
                  ) : selectedConnector.category === "files" ? (
                    <div className="space-y-4">
                      {/* Dropzone */}
                      <div
                        onDragOver={handleDragOver}
                        onDragLeave={handleDragLeave}
                        onDrop={handleDrop}
                        onClick={() => fileInputRef.current?.click()}
                        className={`border border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                          isDragging
                            ? "border-indigo-500 bg-indigo-500/5"
                            : "border-[var(--border)] hover:border-slate-400 bg-[var(--bg)]/50"
                        }`}
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

                        {selectedFile ? (
                          <div className="space-y-1">
                            <p className="text-xs font-medium text-[var(--txt)] flex items-center justify-center gap-1.5">
                              <CheckCircle2 size={14} className="text-emerald-500" />
                              {selectedFile.name}
                            </p>
                            <p className="text-[11px] text-[var(--txt-f)] font-mono">
                              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                            </p>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedFile(null);
                                if (fileInputRef.current) fileInputRef.current.value = "";
                              }}
                              className="text-[11px] text-red-400 hover:underline mt-1 cursor-pointer"
                            >
                              Remove
                            </button>
                          </div>
                        ) : (
                          <div className="space-y-1">
                            <UploadCloud size={20} className="mx-auto text-[var(--txt-m)] mb-2" />
                            <p className="text-xs font-medium text-[var(--txt)]">
                              Drop {getExpectedExtensions(selectedConnector.id).label} file or browse
                            </p>
                            <p className="text-[11px] text-[var(--txt-f)]">
                              Up to 100MB ({getExpectedExtensions(selectedConnector.id).extensions.map((e) => `.${e}`).join(", ")})
                            </p>
                          </div>
                        )}
                      </div>

                      {/* Demo samples shortcuts (Minimal text list, NO PILLS) */}
                      <div className="flex items-center gap-2 text-xs text-[var(--txt-m)] pt-1">
                        <span className="text-[var(--txt-f)]">Sample data:</span>
                        {SAMPLE_DATASETS.slice(0, 3).map((sample, idx) => (
                          <React.Fragment key={sample.id}>
                            <button
                              type="button"
                              onClick={() => handleQuickSample(sample)}
                              className="text-[var(--txt)] hover:text-indigo-400 transition-colors cursor-pointer"
                            >
                              {sample.name}
                            </button>
                            {idx < 2 && <span className="text-[var(--txt-f)]">·</span>}
                          </React.Fragment>
                        ))}
                      </div>
                    </div>
                  ) : (
                    /* Databases */
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-medium mb-1.5">
                          Connection URI
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={connUri}
                            onChange={(e) => setConnUri(e.target.value)}
                            placeholder={selectedConnector.defaultUri}
                            className="flex-1 rounded-md px-3 py-2 text-xs font-mono bg-[var(--bg)] border border-[var(--border)] text-[var(--txt)] focus:outline-none focus:border-indigo-500"
                          />
                          <button
                            type="button"
                            onClick={handleTestPing}
                            disabled={isTesting || !connUri.trim()}
                            className="px-3 py-2 rounded-md border border-[var(--border)] text-xs font-medium hover:bg-[var(--card)] disabled:opacity-40 transition-colors cursor-pointer"
                          >
                            {isTesting ? "Testing..." : "Test"}
                          </button>
                        </div>
                        {testResult && (
                          <p
                            className={`text-[11px] mt-1.5 ${
                              testResult.ok ? "text-emerald-400" : "text-red-400"
                            }`}
                          >
                            {testResult.message}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-xs font-medium mb-1.5">Target Table</label>
                        {dbTables.length > 0 ? (
                          <select
                            value={targetTable}
                            onChange={(e) => setTargetTable(e.target.value)}
                            className="w-full rounded-md px-3 py-2 text-xs font-mono bg-[var(--bg)] border border-[var(--border)] text-[var(--txt)] focus:outline-none cursor-pointer"
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
                            className="w-full rounded-md px-3 py-2 text-xs font-mono bg-[var(--bg)] border border-[var(--border)] text-[var(--txt)] focus:outline-none"
                          />
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer Actions */}
                <div className="pt-4 border-t flex items-center justify-between gap-3 mt-6" style={{ borderColor: "var(--border)" }}>
                  <div className="min-w-0 flex-1">
                    {errorMsg && (
                      <p className="text-xs text-red-400 truncate flex items-center gap-1.5">
                        <AlertCircle size={13} className="shrink-0" />
                        <span>{errorMsg}</span>
                      </p>
                    )}
                  </div>

                  <button
                    type="button"
                    onClick={handleConnect}
                    disabled={isConnecting || hasActiveDataset}
                    className="px-4 py-2 rounded-md font-medium text-xs bg-indigo-600 hover:bg-indigo-500 text-white transition-colors disabled:opacity-40 flex items-center gap-2 cursor-pointer"
                  >
                    {isConnecting && <Loader2 size={13} className="animate-spin" />}
                    <span>Launch Workspace</span>
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
