"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { apiFetch } from "@/lib/api";

interface WorkspaceContextType {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  uploadId?: string;
  profile: any;
  setProfile: (profile: any) => void;
  cleanProfile: any;
  setCleanProfile: (profile: any) => void;
  geminiOk: boolean;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  sourceType: string;
  isSyncingSheets: boolean;
  syncSheets: () => Promise<void>;
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
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [activeTab, setActiveTab] = useState("preview");
  const [uploadId, setUploadId] = useState<string | undefined>();
  const [profile, setProfile] = useState<any>(null);
  const [cleanProfile, setCleanProfile] = useState<any>(null);
  const [geminiOk, setGeminiOk] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sourceType, setSourceType] = useState("csv");
  const [isSyncingSheets, setIsSyncingSheets] = useState(false);
  const [chatSidebarOpen, setChatSidebarOpen] = useState(true);
  const [chatSessions, setChatSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [cleanResult, setCleanResult] = useState<any>(null);
  const [apiError, setApiError] = useState<{ code: number; message: string } | null>(null);

  useEffect(() => {
    let uid = "";
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const urlUid = urlParams.get('upload_id');
      if (urlUid) {
        setUploadId(urlUid);
        uid = urlUid;
      }
    }
    // Initial fetch of workspace state
    const stateUrl = uid ? `/workspace/state?upload_id=${uid}` : "/workspace/state";
    apiFetch(stateUrl).then(async (res) => {
      if (res.ok) {
        const data = await res.json();
        setProfile(data.profile);
        setGeminiOk(data.gemini_ok);
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
    });
  }, []);

  const syncSheets = async () => {
    setIsSyncingSheets(true);
    // implement sync
    setIsSyncingSheets(false);
  };

  const value = {
    activeTab, setActiveTab,
    uploadId, setUploadId,
    profile, setProfile,
    cleanProfile, setCleanProfile,
    geminiOk,
    drawerOpen, setDrawerOpen,
    sourceType,
    isSyncingSheets, syncSheets,
    chatSidebarOpen, setChatSidebarOpen,
    chatSessions, setChatSessions,
    activeSessionId, setActiveSessionId,
    cleanResult, setCleanResult,
    apiError, setApiError,
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
