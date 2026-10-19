"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

import { SheetSyncModalState } from "./SheetSyncModal";

interface WorkspaceContextType {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  uploadId?: string | null;
  setUploadId: (id: string | null) => void;
  profile: any;
  setProfile: (profile: any) => void;
  cleanProfile: any;
  setCleanProfile: (profile: any) => void;
  geminiOk: boolean;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  sourceType: string;
  setSourceType: (type: string) => void;
  isSyncingSheets: boolean;
  syncSheets: () => Promise<any>;
  syncModalState: SheetSyncModalState | null;
  setSyncModalState: (s: SheetSyncModalState | null) => void;
  closeSyncModal: () => void;
  // Chat state
  chatSidebarOpen: boolean;
  setChatSidebarOpen: (open: boolean) => void;
  chatSessions: any[];
  setChatSessions: (sessions: any[]) => void;
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  // Cleanup
  cleanResult: any;
  setCleanResult: (result: any) => void;
  // Error state
  apiError: { code: number; message: string } | null;
  setApiError: (err: { code: number; message: string } | null) => void;
  // Shared access metadata
  shareMeta: any;
  setShareMeta: (meta: any) => void;
  // Initial loading state
  isLoadingWorkspace: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState("preview");
  const [uploadId, setUploadId] = useState<string | undefined>(undefined);
  const [profile, setProfile] = useState<any>(null);
  const [cleanProfile, setCleanProfile] = useState<any>(null);
  const [geminiOk, setGeminiOk] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sourceType, setSourceType] = useState("csv");
  const [isSyncingSheets, setIsSyncingSheets] = useState(false);
  const [syncModalState, setSyncModalState] = useState<SheetSyncModalState | null>(null);
  const [chatSidebarOpen, setChatSidebarOpen] = useState(true);
  const [chatSessions, setChatSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [cleanResult, setCleanResult] = useState<any>(null);
  const [apiError, setApiError] = useState<{ code: number; message: string } | null>(null);
  const [shareMeta, setShareMeta] = useState<any>(null);
  const [isLoadingWorkspace, setIsLoadingWorkspace] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      return !!urlParams.get("upload_id");
    }
    return false;
  });

  useEffect(() => {
    let uid = "";
    let shareToken = "";
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const urlUid = urlParams.get('upload_id');
      const urlToken = urlParams.get('share_token');
      if (urlUid) {
        setUploadId(urlUid);
        uid = urlUid;
      }
      if (urlToken) {
        shareToken = urlToken;
        try {
          sessionStorage.setItem("df_share_token_" + urlUid, urlToken);
        } catch {}
      } else if (urlUid) {
        try {
          shareToken = sessionStorage.getItem("df_share_token_" + urlUid) || "";
        } catch {}
      }
    }

    if (!uid) {
      // No upload ID present yet — stay in workspace and open Ingestion Hub
      setIsLoadingWorkspace(false);
      return;
    }

    setIsLoadingWorkspace(true);

    // Initial fetch of workspace state
    const stateUrl = uid
      ? `/workspace/state?upload_id=${uid}${shareToken ? `&share_token=${shareToken}` : ""}`
      : "/workspace/state";
    apiFetch(stateUrl)
      .then(async (res) => {
        if (res.ok) {
          const data = await res.json();
          setProfile(data.profile);
          setGeminiOk(data.gemini_ok);
          if (data.share_meta) {
            setShareMeta(data.share_meta);
          }
          if (data.source_type) {
            setSourceType(data.source_type);
          }
          if (data.clean_profile) {
            setCleanProfile(data.clean_profile);
          }
        } else if (res.status === 401) {
          if (typeof window !== "undefined") {
            window.location.href = "/?login=1";
          }
        } else if (res.status === 400 || res.status === 403 || res.status === 404) {
          const data = await res.json().catch(() => ({ detail: "An error occurred" }));
          setApiError({ code: res.status, message: data.detail || "An error occurred" });
        } else {
          setApiError({ code: res.status, message: "Unexpected server error" });
        }
      })
      .catch((err) => {
        console.error("Workspace state error:", err);
        setApiError({ code: 500, message: "Failed to connect to workspace backend." });
      })
      .finally(() => {
        setIsLoadingWorkspace(false);
      });
  }, []);

  const closeSyncModal = () => setSyncModalState(null);

  const syncSheets = async () => {
    if (!uploadId) return null;
    setIsSyncingSheets(true);
    try {
      const res = await apiFetch("/workspace/sync-sheets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upload_id: uploadId }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const errMessage = data.detail || data.error || "Failed to sync with Google Sheets";
        setSyncModalState({
          isOpen: true,
          error: errMessage,
        });
        return null;
      }

      if (data.profile) {
        setProfile(data.profile);
      }
      if (data.changes?.has_changes) {
        setCleanProfile(null);
      }
      setSyncModalState({
        isOpen: true,
        result: data,
      });
      return data;
    } catch (err: any) {
      setSyncModalState({
        isOpen: true,
        error: err?.message || "Network error while syncing Google Sheet",
      });
      return null;
    } finally {
      setIsSyncingSheets(false);
    }
  };

  const value = {
    activeTab, setActiveTab,
    uploadId: uploadId ?? null,
    setUploadId: (id: string | null) => setUploadId(id ?? undefined),
    profile, setProfile,
    cleanProfile, setCleanProfile,
    geminiOk,
    drawerOpen, setDrawerOpen,
    sourceType, setSourceType,
    isSyncingSheets, syncSheets,
    syncModalState, setSyncModalState, closeSyncModal,
    chatSidebarOpen, setChatSidebarOpen,
    chatSessions, setChatSessions,
    activeSessionId, setActiveSessionId,
    cleanResult, setCleanResult,
    apiError, setApiError,
    shareMeta, setShareMeta,
    isLoadingWorkspace,
  };

  // (upload_id is now handled in the main useEffect)

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
