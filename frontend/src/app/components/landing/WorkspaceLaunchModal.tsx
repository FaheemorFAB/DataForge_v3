"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
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
import Logo from "../Logo";
import {
  Search,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  UploadCloud,
  Clock,
  Lock,
  User,
  Users,
  FileSpreadsheet,
  Database,
} from "lucide-react";
import { formatBytes } from "@/lib/format";

interface WorkspaceLaunchModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: string;
  initialConnectorId?: string;
  hasActiveDataset?: boolean;
  activeDatasetName?: string;
}

export type ConnectorCategory = "files" | "spreadsheets" | "relational" | "history";

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
  const { user } = useAuth();
  const isLoggedIn = !!user;

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

  // Ingestion History & Workspace Scoping
  const [historyDatasets, setHistoryDatasets] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeHistoryWorkspace, setActiveHistoryWorkspace] = useState<string>("personal");
  const [availableTeams, setAvailableTeams] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    if (!isOpen) return;

    if (!isLoggedIn) {
      setAvailableTeams([]);
      setHistoryDatasets([]);
      if (selectedCategory === "history") {
        setSelectedCategory("all");
      }
      return;
    }

    const currentWs = (typeof window !== "undefined" && localStorage.getItem("df_active_workspace")) || "personal";
    setActiveHistoryWorkspace(currentWs);

    try {
      const cached = localStorage.getItem("df_teams_data");
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed)) {
          setAvailableTeams(parsed.map((t: any) => ({ id: t.id, name: t.name })));
        }
      }
    } catch {}

    // Live sync teams to surface newly invited/created workspaces
    apiFetch("/teams")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.organizations)) {
          const list = data.organizations.map((t: any) => ({ id: t.id, name: t.name }));
          setAvailableTeams(list);
          try {
            localStorage.setItem("df_teams_data", JSON.stringify(list));
          } catch {}
        }
      })
      .catch(() => {});

    loadHistory(currentWs);
  }, [isOpen, isLoggedIn, selectedCategory]);

  const loadHistory = async (wsId: string) => {
    setHistoryLoading(true);
    setHistoryDatasets([]); // Clear immediately to avoid displaying another workspace's datasets
    try {
      const targetWs = wsId || "personal";
      const res = await apiFetch(`/dashboard/init?workspace_id=${encodeURIComponent(targetWs)}`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.recent_uploads)) {
          setHistoryDatasets(data.recent_uploads);
        } else {
          setHistoryDatasets([]);
        }
      } else {
        setHistoryDatasets([]);
      }
    } catch {
      setHistoryDatasets([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSwitchHistoryWorkspace = (wsId: string) => {
    setActiveHistoryWorkspace(wsId);
    try {
      localStorage.setItem("df_active_workspace", wsId);
    } catch {}
    loadHistory(wsId);
  };

  const handleLaunchExistingDataset = (uploadId: string) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("df_last_upload_id", uploadId);
      try {
        sessionStorage.removeItem("df_share_token_" + uploadId);
      } catch {}
    }
    onClose();
    router.push(`/workspace?upload_id=${encodeURIComponent(uploadId)}`);
  };

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

  // Auto-dismiss error notifications after 6 seconds
  useEffect(() => {
    if (!errorMsg) return;
    const timer = setTimeout(() => setErrorMsg(""), 6000);
    return () => clearTimeout(timer);
  }, [errorMsg]);

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
    return selectedCategory === "all" || c.category === selectedCategory;
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

      const effectiveWs =
        activeHistoryWorkspace && activeHistoryWorkspace !== "personal"
          ? activeHistoryWorkspace
          : (typeof window !== "undefined" ? localStorage.getItem("df_active_workspace") : null);
      const targetWorkspaceId = (effectiveWs && effectiveWs !== "personal") ? effectiveWs : undefined;

      if (selectedConnector.category === "spreadsheets") {
        if (selectedConnector.id === "google_sheets") {
          setGenerationStatus("Streaming Google Sheets workbook tabs...");
          const res = await apiFetch("/upload/sheets", {
            method: "POST",
            body: JSON.stringify({
              url: cleanUri,
              sheet_name: cleanTable || undefined,
              workspace_id: targetWorkspaceId,
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
              workspace_id: targetWorkspaceId,
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
        if (targetWorkspaceId) {
          formData.append("workspace_id", targetWorkspaceId);
        }
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
          workspace_id: targetWorkspaceId,
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
        try {
          sessionStorage.removeItem("df_share_token_" + uploadId);
        } catch {}
      }

      setTimeout(() => {
        onClose();
        window.location.href = `/workspace?upload_id=${uploadId}`;
      }, 1000);
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
      selectedConnector.category,
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

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-2.5 sm:p-4 backdrop-blur-sm animate-fadeIn"
      style={{ background: "rgba(0, 0, 0, 0.7)" }}
      onClick={isGeneratingWorkspace ? undefined : onClose}
    >
      {/* Floating Top-Center Notification Banner */}
      {errorMsg && (
        <div
          role="alert"
          className="fixed top-5 left-1/2 -translate-x-1/2 z-[99999] w-[92vw] max-w-md px-4 py-3 rounded-xl border shadow-2xl flex items-center justify-between gap-3 bg-red-950/95 border-red-500/50 text-red-200 backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-200"
        >
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <AlertCircle size={18} className="shrink-0 text-red-400" />
            <span className="text-xs font-semibold leading-snug break-words">
              {errorMsg}
            </span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMsg("")}
            className="shrink-0 text-red-400 hover:text-red-200 p-1 rounded-md transition-colors cursor-pointer"
            aria-label="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}

      <div
        className="w-[90vw] sm:w-full max-w-3xl max-h-[68vh] sm:max-h-[85vh] rounded-xl shadow-2xl overflow-hidden flex flex-col relative animate-slideUp text-[var(--txt)]"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-4 sm:px-6 py-3 sm:py-4 border-b flex items-center justify-between shrink-0"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-2.5 sm:gap-3">
            <div
              className="w-8 h-8 sm:w-9 sm:h-9 rounded-full border-2 border-dotted flex items-center justify-center shrink-0"
              style={{
                borderColor: "var(--accent)",
                background: "var(--glow)",
              }}
            >
              <Logo size={18} showText={false} />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm font-bold tracking-tight" style={{ color: "var(--txt)" }}>
                {isGeneratingWorkspace ? "Opening Workspace" : "Import Data"}
              </h3>
              <p className="text-[10px] sm:text-xs text-[var(--txt-m)] mt-0.5 line-clamp-1">
                {isGeneratingWorkspace
                  ? "Setting up your data session..."
                  : "Select a source to load into your workspace"}
              </p>
            </div>
          </div>

          {!isGeneratingWorkspace && (
            <button
              onClick={onClose}
              className="text-[var(--txt-m)] hover:text-[var(--txt)] p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition-colors cursor-pointer shrink-0"
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
              className="px-4 sm:px-6 border-b flex items-center gap-4 sm:gap-6 text-xs overflow-x-auto no-scrollbar whitespace-nowrap shrink-0"
              style={{ borderColor: "var(--border)" }}
            >
              {[
                { id: "all", label: "All Connectors" },
                { id: "files", label: "Files" },
                { id: "spreadsheets", label: "Cloud Sheets" },
                { id: "relational", label: "Databases" },
                ...(isLoggedIn ? [{ id: "history", label: "Ingestion History" }] : []),
              ].map((cat) => {
                const isActive = selectedCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedCategory(cat.id as any)}
                    className={`py-3 font-medium transition-colors border-b-2 -mb-px cursor-pointer flex items-center gap-1.5 ${
                      isActive
                        ? "border-indigo-500 text-[var(--txt)]"
                        : "border-transparent text-[var(--txt-m)] hover:text-[var(--txt)]"
                    }`}
                  >
                    {cat.id === "history" && <Clock size={12} className={isActive ? "text-indigo-400" : "opacity-60"} />}
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Main Content Area */}
            {isLoggedIn && selectedCategory === "history" ? (
              <div className="p-4 sm:p-6 flex flex-col min-h-0 sm:min-h-[380px] overflow-y-auto minimal-scrollbar flex-1 space-y-4">
                {/* Header & Dynamic Workspace Switcher */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b" style={{ borderColor: "var(--border)" }}>
                  <div>
                    <h4 className="text-xs sm:text-sm font-bold flex items-center gap-2" style={{ color: "var(--txt)" }}>
                      <Clock size={15} style={{ color: "var(--accent)" }} />
                      <span>Ingested Datasets History</span>
                    </h4>
                    <p className="text-[11px] text-[var(--txt-m)] mt-0.5">
                      {activeHistoryWorkspace === "personal"
                        ? "Your private datasets in Personal Space. Click any dataset to immediately open your workspace session."
                        : `Datasets ingested within ${availableTeams.find((t) => t.id === activeHistoryWorkspace)?.name || "this workspace"}.`}
                    </p>
                  </div>

                  {/* Dynamic Workspace Switcher Pills */}
                  {availableTeams.length > 0 && (
                    <div className="flex items-center gap-1.5 p-1 rounded-xl border self-start sm:self-auto shrink-0" style={{ background: "var(--bg)", borderColor: "var(--border)" }}>
                      <button
                        type="button"
                        onClick={() => handleSwitchHistoryWorkspace("personal")}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                        style={{
                          background: activeHistoryWorkspace === "personal" ? "var(--accent)" : "transparent",
                          color: activeHistoryWorkspace === "personal" ? "#fff" : "var(--txt-m)",
                        }}
                      >
                        <User size={12} />
                        <span>Personal Space</span>
                      </button>
                      {availableTeams.map((team) => {
                        const isTeamSel = activeHistoryWorkspace === team.id;
                        return (
                          <button
                            key={team.id}
                            type="button"
                            onClick={() => handleSwitchHistoryWorkspace(team.id)}
                            className="px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                            style={{
                              background: isTeamSel ? "#10b981" : "transparent",
                              color: isTeamSel ? "#fff" : "var(--txt-m)",
                            }}
                          >
                            <Users size={12} />
                            <span className="truncate max-w-[110px]">{team.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* History Content */}
                {!isLoggedIn ? (
                  <div className="p-8 rounded-xl border border-dashed flex flex-col items-center justify-center text-center space-y-3 my-auto" style={{ borderColor: "var(--border)", background: "var(--card)" }}>
                    <div className="w-12 h-12 rounded-2xl flex items-center justify-center border" style={{ background: "rgba(99,102,241,0.1)", borderColor: "rgba(99,102,241,0.25)", color: "var(--accent)" }}>
                      <Lock size={20} />
                    </div>
                    <div className="space-y-1">
                      <h5 className="text-xs font-bold" style={{ color: "var(--txt)" }}>Sign In to View Ingestion History</h5>
                      <p className="text-xs max-w-sm" style={{ color: "var(--txt-m)" }}>
                        Your uploaded datasets and past analyses are securely stored in your account. Sign in to view and resume them instantly.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        onClose();
                        router.push("/login");
                      }}
                      className="px-4 py-2 rounded-xl text-xs font-bold text-white transition-opacity hover:opacity-90 cursor-pointer shadow-md"
                      style={{ background: "var(--accent)" }}
                    >
                      Sign In to Account →
                    </button>
                  </div>
                ) : historyLoading ? (
                  <div className="p-12 flex flex-col items-center justify-center text-center space-y-2 my-auto">
                    <Loader2 size={24} className="animate-spin text-indigo-500" />
                    <span className="text-xs text-[var(--txt-m)] font-medium">Loading workspace history...</span>
                  </div>
                ) : historyDatasets.length === 0 ? (
                  <div className="p-8 rounded-xl border border-dashed flex flex-col items-center justify-center text-center space-y-2 my-auto" style={{ borderColor: "var(--border)", background: "var(--card)" }}>
                    <Database size={24} className="opacity-40" />
                    <h5 className="text-xs font-bold" style={{ color: "var(--txt)" }}>No Datasets Ingested Yet</h5>
                    <p className="text-xs text-[var(--txt-m)] max-w-xs">
                      No datasets have been ingested in this workspace yet. Select a file or connector to upload your first dataset.
                    </p>
                    <button
                      type="button"
                      onClick={() => setSelectedCategory("files")}
                      className="text-xs font-bold underline mt-1 cursor-pointer"
                      style={{ color: "var(--accent)" }}
                    >
                      Upload a file now →
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[320px] overflow-y-auto minimal-scrollbar pr-1">
                    {historyDatasets.map((ds) => (
                      <div
                        key={ds.id}
                        onClick={() => handleLaunchExistingDataset(ds.id)}
                        className="p-3.5 rounded-xl border transition-all flex flex-col justify-between gap-2.5 hover:border-[var(--accent)] hover:shadow-md cursor-pointer group"
                        style={{
                          background: "var(--card)",
                          borderColor: "var(--border)",
                        }}
                      >
                        <div className="space-y-1.5">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex items-center gap-2 truncate">
                              <FileSpreadsheet size={15} style={{ color: "var(--accent)" }} className="shrink-0" />
                              <span className="text-xs font-bold truncate group-hover:text-indigo-400 transition-colors" style={{ color: "var(--txt)" }}>
                                {ds.filename || `Dataset ${ds.id.slice(0, 8)}`}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border shrink-0" style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt-m)" }}>
                              {ds.source_type?.toUpperCase() || "CSV"}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 text-[10px] font-mono flex-wrap" style={{ color: "var(--txt-m)" }}>
                            <span>{ds.rows?.toLocaleString() || 0} rows × {ds.cols || 0} cols</span>
                            <span>•</span>
                            <span className="font-semibold text-emerald-400">
                              {ds.size_human || (ds.size_bytes ? formatBytes(ds.size_bytes) : "—")}
                            </span>
                            <span>•</span>
                            <span>{ds.time_ago || "recently"}</span>
                          </div>
                        </div>

                        <div className="flex items-center justify-between pt-2 border-t text-[11px] font-bold" style={{ borderColor: "var(--border)", color: "var(--accent)" }}>
                          <span>Open in Workspace</span>
                          <span className="transition-transform group-hover:translate-x-1">→</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-12 min-h-0 sm:min-h-[360px] overflow-y-auto minimal-scrollbar flex-1">
                {/* Left Column: Source Selection (5 cols) */}
                <div
                  className="md:col-span-5 border-b md:border-b-0 md:border-r p-3 sm:p-4 flex flex-col gap-2.5 sm:gap-3"
                  style={{ borderColor: "var(--border)" }}
                >
                  {/* List */}
                  <div className="flex-1 overflow-y-auto minimal-scrollbar space-y-1.5 pr-1.5 max-h-[165px] sm:max-h-[340px]">
                    {filteredConnectors.map((c) => {
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
                    })}
                  </div>

                  {/* Mobile Scroll Indicator */}
                  <div className="md:hidden pt-1 flex items-center justify-between text-[10px] text-[var(--txt-m)] border-t border-[var(--border)]/40 shrink-0">
                    <span className="flex items-center gap-1 font-medium">
                      <span>Scroll for more sources</span>
                    </span>
                    <span className="text-[9px] font-mono text-[var(--accent)] font-bold animate-bounce">↓</span>
                  </div>
                </div>

              {/* Right Column: Configuration & Actions (7 cols) */}
              <div className="md:col-span-7 p-3.5 sm:p-6 flex flex-col justify-between overflow-y-auto">
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
                            <p className="text-[11px] font-mono font-semibold text-emerald-400">
                              {formatBytes(selectedFile.size)}
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

                      {/* Recent Ingestion Shortcuts (Hidden completely if user is not logged in) */}
                      {isLoggedIn && historyDatasets.length > 0 && (
                        <div className="flex items-center gap-2 text-xs text-[var(--txt-m)] pt-1 flex-wrap">
                          <span className="text-[var(--txt-f)] flex items-center gap-1">
                            <Clock size={11} style={{ color: "var(--accent)" }} />
                            <span>Recent history:</span>
                          </span>
                          {historyDatasets.slice(0, 3).map((ds, idx) => (
                            <React.Fragment key={ds.id}>
                              <button
                                type="button"
                                onClick={() => handleLaunchExistingDataset(ds.id)}
                                className="text-[var(--txt)] hover:text-indigo-400 transition-colors cursor-pointer max-w-[130px] truncate underline"
                                title={`Open ${ds.filename} (${ds.size_human || (ds.size_bytes ? formatBytes(ds.size_bytes) : "")})`}
                              >
                                {ds.filename}
                              </button>
                              {idx < Math.min(historyDatasets.length - 1, 2) && <span className="text-[var(--txt-f)]">·</span>}
                            </React.Fragment>
                          ))}
                          <button
                            type="button"
                            onClick={() => setSelectedCategory("history")}
                            className="text-indigo-400 hover:underline text-[11px] cursor-pointer ml-1 font-semibold"
                          >
                            All history →
                          </button>
                        </div>
                      )}
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
          )}
          </>
        )}
      </div>
    </div>
  );
}
