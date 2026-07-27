"use client";

import React, { useState, useEffect, useRef } from "react";
import io, { Socket } from "socket.io-client";
import styles from "./dashboard.module.css";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ThemeSwitcher from "../components/ThemeSwitcher";
import Logo from "../components/Logo";

// ── Validation Helpers ──
const V = {
  email(v: string) {
    if (!v) return null;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim()) ? null : "Enter a valid email address";
  },
  cron(v: string) {
    if (!v || !v.trim()) return "Cron expression is required";
    const parts = v.trim().split(/\s+/);
    if (parts.length !== 5) return "Cron must have 5 fields";
    const valid = parts.every((p) => /^(\*|[0-9,\-\/]+)$/.test(p));
    if (!valid) return "Invalid cron expression";
    return null;
  },
};

const timeAgo = (iso: string) => {
  if (!iso) return "";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
};

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const router = useRouter();

  const [activeTab, setActiveTab] = useState("overview");
  const [currentTheme, setCurrentTheme] = useState("");
  const [currentFont, setCurrentFont] = useState("");
  const [isCustomizerOpen, setIsCustomizerOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);

  const [wsConnected, setWsConnected] = useState(false);
  const [newEventCount, setNewEventCount] = useState(0);

  const [initData, setInitData] = useState<any>(null);
  const [stats, setStats] = useState<any>({});
  const [feedItems, setFeedItems] = useState<any[]>([]);
  const [alertCount, setAlertCount] = useState(0);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [alertsChecking, setAlertsChecking] = useState(false);

  const [insights, setInsights] = useState<any[]>([]);
  const [insightSummary, setInsightSummary] = useState("");
  const [insightError, setInsightError] = useState("");
  const [insightsLoading, setInsightsLoading] = useState(false);

  const [reports, setReports] = useState<any[]>([]);
  const [previewReportId, setPreviewReportId] = useState<number | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const [schedules, setSchedules] = useState<any[]>([]);
  const [showNewSchedule, setShowNewSchedule] = useState(false);
  const [schedLoading, setSchedLoading] = useState(false);
  const [newSched, setNewSched] = useState({ cron: "0 9 * * 1", email: "" });
  const [schedErrors, setSchedErrors] = useState({ cron: "", email: "" });

  const [toasts, setToasts] = useState<any[]>([]);
  const toastCtr = useRef(0);

  const [acct, setAcct] = useState<any>({ name: "", avatar: "", avatarDataUri: "", avatarStyle: "lorelei", avatarRollSeed: 0 });
  const [acctSaving, setAcctSaving] = useState(false);
  const [acctMsg, setAcctMsg] = useState("");
  const [acctMsgOk, setAcctMsgOk] = useState(true);
  const [avatarGenerating, setAvatarGenerating] = useState(false);
  const [avatarStyles, setAvatarStyles] = useState<any[]>([]);

  const [cleanedDatasets, setCleanedDatasets] = useState<any[]>([]);
  const [edaReports, setEdaReports] = useState<any[]>([]);
  const [acctDatasetsLoading, setAcctDatasetsLoading] = useState(false);
  const [acctEdaLoading, setAcctEdaLoading] = useState(false);

  const [assets, setAssets] = useState<any>({ datasets: [], models: [], reports: [] });
  const [assetsLoading, setAssetsLoading] = useState(false);
  const [assetsRenaming, setAssetsRenaming] = useState<any>({});
  
  const startRename = (type: string, item: any) => {
    // This is a placeholder since we are not fully implementing renaming right now
    setAssetsRenaming((prev: any) => ({ ...prev, [item.id || item.upload_id]: true }));
  };
  
  const commitRename = (type: string, item: any) => {
    // Placeholder
    setAssetsRenaming((prev: any) => ({ ...prev, [item.id || item.upload_id]: false }));
  };

  const checkAlerts = () => {};
  const resolveAlert = (id: string) => {};
  const rerollAvatar = () => {};
  const generateAvatar = () => {};
  const selectStyle = (id: string) => {};
  const saveAccount = () => {};
  const [assetsEditName, setAssetsEditName] = useState<any>({});
  const [restoringId, setRestoringId] = useState<number | null>(null);

  const feedScrollRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<Socket | null>(null);

  // ── apiFetch ──
  const apiFetch = async (url: string, opts: any = {}) => {
    opts.headers = { Accept: "application/json", ...(opts.headers || {}) };
    try {
      const res = await fetch(`/api${url.startsWith("/api") ? url.slice(4) : url}`, opts);
      if (res.status === 401) {
        window.location.href = "/login";
        return { ok: false, status: 401, data: null, error: "Not authenticated" };
      }
      const ct = res.headers.get("content-type") || "";
      if (!ct.includes("application/json")) {
        return { ok: false, status: res.status, data: null, error: `Server returned non-JSON (${res.status})` };
      }
      const data = await res.json();
      return { ok: res.ok, status: res.status, data, error: data.error || null };
    } catch (e: any) {
      return { ok: false, status: 0, data: null, error: "Network error: " + e.message };
    }
  };

  const pushToast = (t: any) => {
    toastCtr.current++;
    const id = toastCtr.current;
    setToasts((prev) => [...prev, { ...t, id, leaving: false }]);
    setTimeout(() => dismissToast(id), 5500);
  };

  const dismissToast = (id: number) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)));
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 280);
  };

  const resumeProject = async (uploadId: number, hashHash: string = "") => {
    setRestoringId(uploadId);
    try {
      const { ok, data, error } = await apiFetch(`/restore/${uploadId}`, { method: "POST" });
      if (!ok || data?.error) {
        pushToast({ type: "alert", icon: "⚠️", title: "Restore Failed", body: error || data?.error || "Unknown error" });
        return;
      }

      sessionStorage.setItem('restore_state', JSON.stringify({
        clean_meta: data.clean_meta || null,
        automl_meta: data.automl_meta || null,
        has_eda: data.has_eda || false,
        chat_history: data.chat_history || [],
      }));

      router.push(`/workspace?upload_id=${encodeURIComponent(uploadId)}${hashHash}`);
    } catch (e: any) {
      pushToast({ type: "alert", icon: "⚠️", title: "Network Error", body: e.message });
    } finally {
      setRestoringId(null);
    }
  };

  // ── Init ──
  useEffect(() => {
    const init = async () => {
      const { ok, data, error } = await apiFetch("/dashboard/init");
      if (!ok) {
        setError(error || "Failed to load dashboard");
        setLoading(false);
        return;
      }
      setInitData(data);
      setStats(data.stats || {});
      setAlertCount(data.alert_count || 0);
      setReports(data.recent_reports || []);
      setPreviewReportId(data.recent_reports?.[0]?.id || null);

      const _feed = (data.recent_analyses || []).map((an: any, i: number) => ({
        id: `seed-${i}`,
        type: an.type,
        label: an.label,
        icon: an.icon,
        summary: an.summary,
        filename: an.filename,
        time_ago: an.time_ago,
        isNew: false,
      }));
      setFeedItems(_feed);

      setAcct({
        name: data.user.name || "",
        avatar: data.user.avatar || "",
        avatarDataUri: data.user.avatar || "",
        avatarStyle: "lorelei",
        avatarRollSeed: 0
      });

      setLoading(false);

      // Sub-fetches
      loadAlerts();
      loadReports();
      loadSchedules();

      // WS
      const socket = io({ transports: ["websocket", "polling"], path: "/socket.io" });
      socketRef.current = socket;

      socket.on("connect", () => setWsConnected(true));
      socket.on("disconnect", () => setWsConnected(false));
      socket.on("connect_error", () => setWsConnected(false));

      socket.on("activity", (d) => onActivity(d));
      socket.on("stats_update", (d) => setStats((prev: any) => ({ ...prev, ...d })));
      socket.on("alert", (d) => {
        setAlertCount((prev) => prev + 1);
        setAlerts((prev) => [{
          id: Date.now(), rule: d.rule, message: d.message,
          severity: d.severity, filename: d.filename, triggered_at: d.ts,
        }, ...prev]);
        pushToast({
          type: "alert",
          icon: d.severity === "critical" ? "🚨" : "⚠️",
          title: `Alert: ${d.rule}`,
          body: d.message,
        });
      });
      socket.on("report_ready", (d) => {
        setPreviewReportId(d.report_id);
        loadReports();
        pushToast({ type: "report", icon: "📄", title: "Report Ready", body: `Generated for ${d.filename || "dataset"}` });
      });
      socket.on("insight_ready", (d) => {
        pushToast({ type: "info", icon: "💡", title: `${d.count} Insights Ready`, body: `${d.dataset_type} · ${d.filename}` });
      });
    };
    init();

    return () => {
      if (socketRef.current) socketRef.current.disconnect();
    };
  }, []);

  const onActivity = (d: any) => {
    const icons: any = { eda: "📊", automl: "🤖", clean: "🧹", query: "💬", insights: "💡", report: "📄" };
    const labels: any = { eda: "EDA", automl: "AutoML", clean: "Cleaning", query: "AI Query", insights: "Insights", report: "Report" };
    const item = {
      id: Date.now() + Math.random(),
      type: d.type,
      label: labels[d.type] || d.type,
      icon: icons[d.type] || "⚡",
      summary: d.summary,
      filename: d.filename,
      time_ago: "just now",
      isNew: true,
    };
    setFeedItems((prev) => {
      const nw = [item, ...prev];
      if (nw.length > 60) nw.pop();
      return nw;
    });
    setNewEventCount((prev) => prev + 1);

    setTimeout(() => {
      setFeedItems((prev) => prev.map((x) => (x.id === item.id ? { ...x, isNew: false } : x)));
      setNewEventCount((prev) => Math.max(0, prev - 1));
    }, 5000);

    if (feedScrollRef.current) feedScrollRef.current.scrollTop = 0;

    pushToast({ type: "info", icon: icons[d.type] || "⚡", title: `${labels[d.type] || d.type} complete`, body: d.summary || d.filename || "" });
  };

  // Watches for activeTab
  useEffect(() => {
    if (activeTab === "account") {
      loadAccountDatasets();
      loadEdaReports();
      if (avatarStyles.length === 0) loadAvatarStyles();
    }
    if (activeTab === "assets" && !assetsLoading && assets.datasets.length === 0 && assets.models.length === 0 && assets.reports.length === 0) {
      loadAssets();
    }
  }, [activeTab]);

  // Loaders
  const loadAlerts = async () => {
    const { ok, data } = await apiFetch("/alerts");
    if (ok && Array.isArray(data)) {
      setAlerts(data);
      setAlertCount(data.length);
    }
  };
  const loadReports = async () => {
    const { ok, data } = await apiFetch("/reports");
    if (ok && Array.isArray(data)) setReports(data);
  };
  const loadSchedules = async () => {
    const { ok, data } = await apiFetch("/schedules");
    if (ok && Array.isArray(data)) setSchedules(data);
  };
  const loadAccountDatasets = async () => {
    if (cleanedDatasets.length > 0) return;
    setAcctDatasetsLoading(true);
    const { ok, data } = await apiFetch("/account/datasets");
    setAcctDatasetsLoading(false);
    if (ok && Array.isArray(data)) setCleanedDatasets(data);
  };
  const loadEdaReports = async () => {
    if (edaReports.length > 0) return;
    setAcctEdaLoading(true);
    const { ok, data } = await apiFetch("/account/eda-reports");
    setAcctEdaLoading(false);
    if (ok && Array.isArray(data)) setEdaReports(data);
  };
  const loadAssets = async () => {
    setAssetsLoading(true);
    const { ok, data } = await apiFetch("/assets");
    setAssetsLoading(false);
    if (ok && data) setAssets({ datasets: data.datasets || [], models: data.models || [], reports: data.reports || [] });
  };
  const loadAvatarStyles = async () => {
    const STYLE_LABELS: any = {
      'lorelei': 'Lorelei', 'avataaars': 'Avataaars', 'bottts': 'Bottts',
      'thumbs': 'Thumbs', 'notionists': 'Notion', 'adventurer': 'Adventurer',
      'fun-emoji': 'Emoji', 'pixel-art': 'Pixel', 'micah': 'Micah',
      'personas': 'Personas', 'open-peeps': 'Peeps', 'shapes': 'Shapes',
      'identicon': 'Identicon', 'rings': 'Rings', 'croodles': 'Croodles',
    };
    const ids = ['lorelei', 'avataaars', 'bottts', 'thumbs', 'notionists', 'adventurer', 'fun-emoji', 'pixel-art', 'micah', 'personas', 'open-peeps', 'shapes', 'identicon', 'rings', 'croodles'];
    const seed = acct.name || "user";
    const previews = await Promise.all(ids.map(async (id) => {
      try {
        const r = await apiFetch("/account/avatar/generate", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ seed, style: id }),
        });
        return { id, label: STYLE_LABELS[id] || id, preview: r.ok ? r.data.data_uri : null };
      } catch { return { id, label: STYLE_LABELS[id] || id, preview: null }; }
    }));
    setAvatarStyles(previews);
  };

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "assets", label: "Assets" },
  ];

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-white">Loading Dashboard...</div>;
  }
  if (error) {
    return <div className="min-h-screen flex items-center justify-center text-red-500">{error}</div>;
  }

  const user = initData?.user || {};

  return (
    <>
      <div className={styles.noise}></div>

      {/* TOASTS */}
      <div className="fixed bottom-6 right-6 z-[100] space-y-2 pointer-events-none" style={{ maxWidth: "380px" }}>
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`${styles.toast} pointer-events-auto ${toast.leaving ? styles.toastLeave : styles.toastEnter}`}
            style={{
              background: toast.type === "alert" ? "rgba(15,5,5,.94)" : toast.type === "report" ? "rgba(5,15,15,.94)" : "rgba(10,10,11,.94)",
              borderColor: toast.type === "alert" ? "rgba(239,68,68,.3)" : toast.type === "report" ? "rgba(20,184,166,.3)" : "var(--border)",
            }}
          >
            <div className="text-lg flex-shrink-0">{toast.icon}</div>
            <div className="flex-1 min-w-0">
              <p className="font-bold text-xs" style={{ color: "var(--txt)" }}>{toast.title}</p>
              <p className="text-[11px] mt-0.5 truncate" style={{ color: "var(--txt-m)" }}>{toast.body}</p>
            </div>
            <button onClick={() => dismissToast(toast.id)} className="flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity" style={{ color: "var(--txt-m)" }}>
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2"><line x1="1" y1="1" x2="11" y2="11" /><line x1="11" y1="1" x2="1" y2="11" /></svg>
            </button>
          </div>
        ))}
      </div>

      {/* NAV */}
      <nav className="sticky top-0 z-30 flex items-center gap-2 px-3 md:px-5 border-b backdrop-blur-md" style={{ background: "var(--nav)", borderColor: "var(--border)", height: "52px" }}>
        <Link href="/" className="flex items-center gap-2 flex-shrink-0 no-underline">
          <Logo size={24} textSize={16} />
        </Link>
        <div className="w-px h-5 flex-shrink-0" style={{ background: "var(--border)" }}></div>
        <Link href="/workspace" className={`${styles.btnP} text-[10px] py-1.5 px-2.5`}>
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          <span className="hidden sm:inline">Workspace</span>
        </Link>
        <div className="flex-1"></div>

        <ThemeSwitcher />

        {/* Alert Bell */}
        <button onClick={() => setActiveTab("alerts")} className={`relative ${styles.ibt} mr-1`} title="Alerts">
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full text-[9px] font-black flex items-center justify-center" style={{ background: "#ef4444", color: "#fff" }}>
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}
        </button>

        {/* Profile */}
        <div className="relative">
          <button onClick={() => setIsProfileOpen(!isProfileOpen)} className="flex items-center gap-2 pl-2 pr-1 py-1 rounded-lg border transition-colors" style={{ borderColor: isProfileOpen ? "var(--accent)" : "var(--border)" }}>
            {acct.avatarDataUri ? (
              <img src={acct.avatarDataUri} className="w-6 h-6 rounded-full object-cover" alt="" />
            ) : user.avatar ? (
              <img src={user.avatar} className="w-6 h-6 rounded-full" alt="" />
            ) : (
              <div className="w-6 h-6 rounded-full flex items-center justify-center font-bold text-[10px]" style={{ background: "var(--accent)", color: "#fff" }}>
                {(user.name || "U")[0].toUpperCase()}
              </div>
            )}
            <span className="hidden sm:block font-bold text-[11px]" style={{ color: "var(--txt)" }}>{acct.name || user.name || user.email || "User"}</span>
            <svg className={`w-3 h-3 transition-transform ${isProfileOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ color: "var(--txt-m)" }}><path d="M6 9l6 6 6-6" /></svg>
          </button>
          {isProfileOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setIsProfileOpen(false)}></div>
              <div className="absolute right-0 mt-2 w-48 rounded-xl py-1 z-50 shadow-xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                <div className="px-4 py-3 border-b" style={{ borderColor: "var(--border)" }}>
                  <p className="font-bold text-xs truncate" style={{ color: "var(--txt)" }}>{acct.name || user.name || "User"}</p>
                  <p className="text-[10px] truncate mt-0.5" style={{ color: "var(--txt-m)" }}>{user.email || ""}</p>
                </div>
                <Link href="/" className="flex items-center gap-2 px-4 py-2 text-xs font-medium hover:opacity-80 transition-opacity" style={{ color: "var(--txt-m)", textDecoration: "none" }}>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
                  New Analysis
                </Link>
                <button onClick={() => { setIsProfileOpen(false); setActiveTab("account"); }} className="w-full flex items-center gap-2 px-4 py-2 text-xs font-medium hover:opacity-80 transition-opacity text-left" style={{ color: "var(--txt-m)", background: "none", border: "none", cursor: "pointer" }}>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                  My Account
                </button>
                <a href="/api/logout" className="flex items-center gap-2 px-4 py-2 text-xs font-medium hover:opacity-80 transition-opacity" style={{ color: "#ef4444", textDecoration: "none" }}>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" /></svg>
                  Sign Out
                </a>
              </div>
            </>
          )}
        </div>
      </nav>

      {/* MAIN */}
      <main className="max-w-6xl mx-auto px-4 md:px-6 py-7 space-y-6">

        {/* Welcome */}
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            {user.avatar && <img src={user.avatar} className="w-12 h-12 rounded-full hidden sm:block" style={{ border: "2px solid var(--border)" }} />}
            <div>
              <p className={`${styles.sl} mb-1`}>Welcome back</p>
              <h1 className={`text-2xl md:text-3xl font-black tracking-tight ${styles.gradTxt}`}>{user.name ? user.name.split(" ")[0] : "Analyst"}</h1>
              <p className="text-xs mt-0.5" style={{ color: "var(--txt-m)" }}>{user.email}</p>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <div className={styles.statCard}>
            <div className="flex items-center justify-between mb-3"><p className={styles.sl}>Uploads</p>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "var(--glow)" }}>
                <svg className="w-4 h-4" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              </div>
            </div>
            <p className={styles.statNum} style={{ color: "var(--accent)" }}>{stats.uploads}</p>
          </div>
          <div className={styles.statCard}>
            <div className="flex items-center justify-between mb-3"><p className={styles.sl}>Analyses</p>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(139,92,246,.12)" }}>
                <svg className="w-4 h-4" style={{ color: "#a78bfa" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
              </div>
            </div>
            <p className={styles.statNum} style={{ color: "#a78bfa" }}>{stats.analyses}</p>
          </div>
          <div className={styles.statCard}>
            <div className="flex items-center justify-between mb-3"><p className={styles.sl}>Models</p>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(16,185,129,.12)" }}>
                <svg className="w-4 h-4" style={{ color: "#10b981" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
              </div>
            </div>
            <p className={styles.statNum} style={{ color: "#10b981" }}>{stats.models}</p>
          </div>
          <div className={styles.statCard}>
            <div className="flex items-center justify-between mb-3"><p className={styles.sl}>AI Queries</p>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: "rgba(245,158,11,.12)" }}>
                <svg className="w-4 h-4" style={{ color: "#fbbf24" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
              </div>
            </div>
            <p className={styles.statNum} style={{ color: "#fbbf24" }}>{stats.queries}</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 p-1 rounded-xl" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          {tabs.map((tab) => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`${styles.tabBtn} ${activeTab === tab.id ? styles.active : ""} flex items-center gap-1.5`}>
              <span>{tab.label}</span>
              {tab.id === "alerts" && alertCount > 0 && (
                <span className="w-4 h-4 rounded-full text-[9px] font-black flex items-center justify-center" style={{ background: "#ef4444", color: "#fff" }}>{alertCount}</span>
              )}
            </button>
          ))}
        </div>

        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
            {/* Recent Uploads */}
            <div className={`lg:col-span-3 ${styles.gc} rounded-2xl overflow-hidden`}>
              <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                <div><p className="font-bold text-sm" style={{ color: "var(--txt)" }}>Recent Uploads</p><p className={`${styles.sl} mt-0.5`}>Last {initData.recent_uploads.length} datasets</p></div>
                <Link href="/" className="text-[10px] font-bold uppercase tracking-widest hover:opacity-70 transition-opacity" style={{ color: "var(--accent)", textDecoration: "none" }}>+ Upload</Link>
              </div>
              {initData.recent_uploads.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className={styles.dt}>
                    <thead><tr><th>File</th><th>Src</th><th>Rows</th><th>Cols</th><th>Missing</th><th>When</th></tr></thead>
                    <tbody>
                      {initData.recent_uploads.map((up: any) => (
                        <tr key={up.id}>
                          <td><div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded flex items-center justify-center text-[8px] font-black flex-shrink-0" style={{ background: "var(--accent)", color: "#fff" }}>{up.source_type === "sheets" ? "GS" : "CSV"}</div>
                            <span className="font-medium truncate" style={{ color: "var(--txt)", maxWidth: "140px" }}>{up.filename}</span>
                          </div></td>
                          <td><span className={styles.badge} style={{ background: "rgba(46,91,255,.07)", color: "var(--txt-m)", border: "1px solid var(--border)" }}>{up.source_type || "csv"}</span></td>
                          <td className="font-mono">{up.rows.toLocaleString()}</td>
                          <td className="font-mono">{up.cols}</td>
                          <td className="font-mono" style={{ color: up.missing_pct > 10 ? "#ef4444" : up.missing_pct > 2 ? "#fbbf24" : "#10b981" }}>{up.missing_pct}%</td>
                          <td style={{ color: "var(--txt-m)" }}>{up.time_ago}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-14 text-center">
                  <p className="font-bold text-sm mb-1" style={{ color: "var(--txt)" }}>No uploads yet</p>
                  <Link href="/" className={`${styles.btnP} text-xs mt-2`}>Upload CSV</Link>
                </div>
              )}
            </div>

            {/* Live Feed */}
            <div className={`lg:col-span-2 ${styles.gc} rounded-2xl overflow-hidden flex flex-col`}>
              <div className="px-5 py-4 border-b flex items-center justify-between flex-shrink-0" style={{ borderColor: "var(--border)" }}>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-bold text-sm" style={{ color: "var(--txt)" }}>Live Activity</p>
                    <div className={`${styles.ld} ${wsConnected ? "" : styles.offline}`}></div>
                  </div>
                  <p className={`${styles.sl} mt-0.5`}>Real-time analysis events</p>
                </div>
                {newEventCount > 0 && (
                  <span className={styles.badge} style={{ background: "rgba(46,91,255,.12)", color: "var(--accent)", border: "1px solid rgba(46,91,255,.25)" }}>
                    {newEventCount} new
                  </span>
                )}
              </div>
              <div className="overflow-y-auto flex-1 p-3 space-y-1" style={{ maxHeight: "430px" }} ref={feedScrollRef}>
                {feedItems.length > 0 ? feedItems.map((item) => (
                  <div key={item.id} className={`${styles.feedItem} flex items-start gap-3 p-3 rounded-xl transition-all`} style={{ background: item.isNew ? "var(--glow)" : "rgba(255,255,255,.02)", boxShadow: item.isNew ? "inset 0 0 0 1px var(--border)" : "" }}>
                    <span className="text-base leading-none mt-0.5 flex-shrink-0">{item.icon}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                        <span className={`${styles.badge} ${styles["badge" + item.type.charAt(0).toUpperCase() + item.type.slice(1)]}`}>{item.label}</span>
                        {item.isNew && <span className={styles.badge} style={{ background: "var(--glow)", color: "var(--accent)", border: "1px solid var(--border)", fontSize: ".55rem" }}>NEW</span>}
                      </div>
                      {item.filename && <p className="text-[10px] font-medium truncate" style={{ color: "var(--txt)" }}>{item.filename}</p>}
                      {item.summary && <p className="text-[10px] truncate mt-0.5" style={{ color: "var(--txt-m)" }}>{item.summary}</p>}
                      <p className="text-[9px] mt-1 opacity-60" style={{ color: "var(--txt-m)" }}>{item.time_ago}</p>
                    </div>
                  </div>
                )) : (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3" style={{ background: "var(--glow)" }}>
                      <svg className="w-5 h-5" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                    </div>
                    <p className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>Waiting for events</p>
                    <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>Run analyses in the workspace</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ASSETS TAB */}
        {activeTab === "assets" && (
          <div className="space-y-6">
            <div className={`flex items-center justify-between px-5 py-4 ${styles.gc} rounded-2xl`}>
              <div><p className="font-bold text-sm" style={{ color: "var(--txt)" }}>My Assets</p><p className={`${styles.sl} mt-0.5`}>Manage datasets, models, and reports</p></div>
              <button onClick={loadAssets} disabled={assetsLoading} className={styles.btnS}>
                <svg className={`w-4 h-4 ${assetsLoading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                {assetsLoading ? "Refreshing..." : "Refresh"}
              </button>
            </div>

            {/* Datasets */}
            <div className={`${styles.gc} rounded-2xl overflow-hidden`}>
              <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                <p className="font-bold text-sm" style={{ color: "var(--txt)" }}>Datasets</p>
                <span className={styles.badge} style={{ background: "rgba(16,185,129,.1)", color: "#10b981", border: "1px solid rgba(16,185,129,.25)" }}>{assets.datasets.length} total</span>
              </div>
              {assets.datasets.length > 0 ? (
                <table className={styles.dt}>
                  <thead><tr><th>Name</th><th>Rows</th><th>Cols</th><th>Missing</th><th>Uploaded</th><th>Actions</th></tr></thead>
                  <tbody>
                    {assets.datasets.map((d: any) => (
                      <tr key={d.id}>
                        <td>
                          {!assetsRenaming[d.id] ? (
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded flex items-center justify-center text-[8px] font-black flex-shrink-0" style={{ background: "var(--accent)", color: "#fff" }}>
                                {d.source_type === "sheets" ? "GS" : d.filename.match(/\.xlsx?$/i) ? "XLS" : "CSV"}
                              </div>
                              <span className="font-medium truncate" style={{ color: "var(--txt)", maxWidth: "200px" }}>{d.label || d.filename}</span>
                            </div>
                          ) : (
                            <input
                              value={assetsEditName[d.id] || ""}
                              onChange={(e) => setAssetsEditName((prev: any) => ({ ...prev, [d.id]: e.target.value }))}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") commitRename("dataset", d);
                                if (e.key === "Escape") setAssetsRenaming((prev: any) => ({ ...prev, [d.id]: false }));
                              }}
                              className="px-2 py-1 rounded-lg text-xs outline-none w-48"
                              style={{ background: "var(--surface)", border: "1px solid var(--accent)", color: "var(--txt)" }}
                              autoFocus
                            />
                          )}
                        </td>
                        <td className="font-mono">{d.rows.toLocaleString()}</td>
                        <td className="font-mono">{d.cols}</td>
                        <td className="font-mono" style={{ color: d.missing_pct > 10 ? "#ef4444" : d.missing_pct > 2 ? "#fbbf24" : "#10b981" }}>{d.missing_pct}%</td>
                        <td style={{ color: "var(--txt-m)" }}>{timeAgo(d.uploaded_at)}</td>
                        <td>
                          <div className="flex items-center gap-1.5">
                            {!assetsRenaming[d.id] ? (
                              <button onClick={() => startRename("dataset", d)} className={styles.badge} style={{ background: "rgba(46,91,255,.08)", color: "var(--accent)", border: "1px solid rgba(46,91,255,.2)" }}>Rename</button>
                            ) : (
                              <button onClick={() => commitRename("dataset", d)} className={styles.badge} style={{ background: "rgba(16,185,129,.1)", color: "#10b981", border: "1px solid rgba(16,185,129,.25)" }}>Save</button>
                            )}
                            <button onClick={() => resumeProject(d.id)} disabled={restoringId === d.id} className={styles.badge} style={{ background: "rgba(255,255,255,.04)", color: "var(--txt-m)", border: "1px solid var(--border)", cursor: "pointer" }}>
                              {restoringId === d.id ? "Opening..." : "Open"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>No datasets</p>
                  <Link href="/" className={`${styles.btnP} text-xs mt-2`}>Upload CSV</Link>
                </div>
              )}
            </div>

            {/* Models */}
            <div className={`${styles.gc} rounded-2xl overflow-hidden`}>
              <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                <p className="font-bold text-sm" style={{ color: "var(--txt)" }}>AutoML Models</p>
                <span className={styles.badge} style={{ background: "rgba(139,92,246,.1)", color: "#a78bfa", border: "1px solid rgba(139,92,246,.25)" }}>{assets.models.length} total</span>
              </div>
              {assets.models.length > 0 ? (
                <table className={styles.dt}>
                  <thead><tr><th>Model Name</th><th>Type</th><th>Trained On</th><th>Actions</th></tr></thead>
                  <tbody>
                    {assets.models.map((m: any) => (
                      <tr key={m.id}>
                        <td>
                          {!assetsRenaming["m_" + m.id] ? (
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded flex items-center justify-center text-[8px] font-black flex-shrink-0" style={{ background: "rgba(139,92,246,.2)", color: "#a78bfa" }}>AI</div>
                              <span className="font-medium truncate" style={{ color: "var(--txt)", maxWidth: "200px" }}>{m.label || m.model_name || "Model"}</span>
                            </div>
                          ) : (
                            <input
                              value={assetsEditName["m_" + m.id] || ""}
                              onChange={(e) => setAssetsEditName((prev: any) => ({ ...prev, ["m_" + m.id]: e.target.value }))}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") commitRename("model", m);
                                if (e.key === "Escape") setAssetsRenaming((prev: any) => ({ ...prev, ["m_" + m.id]: false }));
                              }}
                              className="px-2 py-1 rounded-lg text-xs outline-none w-48"
                              style={{ background: "var(--surface)", border: "1px solid var(--accent)", color: "var(--txt)" }}
                              autoFocus
                            />
                          )}
                        </td>
                        <td><span className={styles.badge} style={{ background: "rgba(139,92,246,.08)", color: "#a78bfa", border: "1px solid rgba(139,92,246,.2)" }}>{m.model_type}</span></td>
                        <td style={{ color: "var(--txt-m)" }}>{timeAgo(m.created_at)}</td>
                        <td>
                          <div className="flex items-center gap-1.5">
                            {!assetsRenaming["m_" + m.id] ? (
                              <button onClick={() => startRename("model", m)} className={styles.badge} style={{ background: "rgba(46,91,255,.08)", color: "var(--accent)", border: "1px solid rgba(46,91,255,.2)" }}>Rename</button>
                            ) : (
                              <button onClick={() => commitRename("model", m)} className={styles.badge} style={{ background: "rgba(16,185,129,.1)", color: "#10b981", border: "1px solid rgba(16,185,129,.25)" }}>Save</button>
                            )}
                            <button onClick={() => resumeProject(m.upload_id, "#automl")} disabled={restoringId === m.upload_id} className={styles.badge} style={{ background: "rgba(255,255,255,.04)", color: "var(--txt-m)", border: "1px solid var(--border)", cursor: "pointer" }}>
                              {restoringId === m.upload_id ? "Opening..." : "View"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>No models trained</p>
                </div>
              )}
            </div>

            {/* Reports */}
            <div className={`${styles.gc} rounded-2xl overflow-hidden`}>
              <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                <p className="font-bold text-sm" style={{ color: "var(--txt)" }}>EDA Reports</p>
                <span className={styles.badge} style={{ background: "rgba(20,184,166,.1)", color: "#2dd4bf", border: "1px solid rgba(20,184,166,.25)" }}>{assets.reports.length} reports</span>
              </div>
              {assets.reports.length > 0 ? (
                <table className={styles.dt}>
                  <thead><tr><th>Name</th><th>Dataset</th><th>Generated</th><th>Actions</th></tr></thead>
                  <tbody>
                    {assets.reports.map((r: any) => (
                      <tr key={r.id}>
                        <td>
                          {!assetsRenaming["r_" + r.id] ? (
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded flex items-center justify-center text-[8px] font-black flex-shrink-0" style={{ background: "rgba(20,184,166,.2)", color: "#2dd4bf" }}>EDA</div>
                              <span className="font-medium truncate" style={{ color: "var(--txt)", maxWidth: "200px" }}>{r.label || r.filename || "EDA Report"}</span>
                            </div>
                          ) : (
                            <input
                              value={assetsEditName["r_" + r.id] || ""}
                              onChange={(e) => setAssetsEditName((prev: any) => ({ ...prev, ["r_" + r.id]: e.target.value }))}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") commitRename("report", r);
                                if (e.key === "Escape") setAssetsRenaming((prev: any) => ({ ...prev, ["r_" + r.id]: false }));
                              }}
                              className="px-2 py-1 rounded-lg text-xs outline-none w-48"
                              style={{ background: "var(--surface)", border: "1px solid var(--accent)", color: "var(--txt)" }}
                              autoFocus
                            />
                          )}
                        </td>
                        <td style={{ color: "var(--txt-m)" }}>{r.filename || "—"}</td>
                        <td style={{ color: "var(--txt-m)" }}>{r.time_ago}</td>
                        <td>
                          <div className="flex items-center gap-1.5">
                            {!assetsRenaming["r_" + r.id] ? (
                              <button onClick={() => startRename("report", r)} className={styles.badge} style={{ background: "rgba(46,91,255,.08)", color: "var(--accent)", border: "1px solid rgba(46,91,255,.2)" }}>Rename</button>
                            ) : (
                              <button onClick={() => commitRename("report", r)} className={styles.badge} style={{ background: "rgba(16,185,129,.1)", color: "#10b981", border: "1px solid rgba(16,185,129,.25)" }}>Save</button>
                            )}
                            <button onClick={() => resumeProject(r.upload_id, "#eda")} disabled={restoringId === r.upload_id} className={styles.badge} style={{ background: "rgba(255,255,255,.04)", color: "var(--txt-m)", border: "1px solid var(--border)", cursor: "pointer" }}>
                              {restoringId === r.upload_id ? "Opening..." : "View"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>No EDA reports yet</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* INSIGHTS TAB */}
        {activeTab === "insights" && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div><p className="font-bold" style={{ color: "var(--txt)" }}>Automated Insights</p><p className={`${styles.sl} mt-0.5`}>AI-generated intelligence from your latest dataset</p></div>
              <button onClick={async () => {
                setInsightsLoading(true); setInsightError("");
                const { ok, data, error } = await apiFetch("/insights/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ top_n: 8, use_gemini: true }) });
                setInsightsLoading(false);
                if (!ok) { setInsightError(error); return; }
                setInsights(data.insights || []); setInsightSummary(data.summary || "");
              }} disabled={insightsLoading} className={styles.btnP}>
                <svg className={`w-4 h-4 ${insightsLoading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24">
                  {insightsLoading ? (
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                  )}
                </svg>
                {insightsLoading ? "Analysing..." : "Run Insights"}
              </button>
            </div>
            {insightSummary && (
              <div className="p-5 rounded-2xl" style={{ background: "rgba(99,102,241,.07)", border: "1px solid rgba(99,102,241,.2)" }}>
                <div className="flex items-center gap-2 mb-3">
                  <svg className="w-4 h-4" style={{ color: "#818cf8" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                  <p className="font-bold text-xs" style={{ color: "#818cf8" }}>AI Executive Summary</p>
                </div>
                <div className="text-sm leading-relaxed" style={{ color: "var(--txt)" }}>{insightSummary}</div>
              </div>
            )}
            {insightError && (
              <div className="p-4 rounded-xl" style={{ background: "rgba(239,68,68,.07)", border: "1px solid rgba(239,68,68,.2)" }}>
                <p className="text-xs font-bold text-red-400">{insightError}</p>
              </div>
            )}
            {insights.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {insights.map((ins, i) => (
                  <div key={i} className={styles.insightCard}>
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-sm leading-tight" style={{ color: "var(--txt)" }}>{ins.title}</p>
                        <p className="text-xs mt-1 leading-relaxed" style={{ color: "var(--txt-m)" }}>{ins.description}</p>
                      </div>
                      <span className={`${styles.badge} flex-shrink-0`} style={{ background: "rgba(99,102,241,.1)", color: "#818cf8", border: "1px solid rgba(99,102,241,.2)" }}>{ins.type}</span>
                    </div>
                    <div className={styles.impBar}><div className={styles.impFill} style={{ width: (ins.importance * 100).toFixed(0) + "%" }}></div></div>
                    <p className="text-[10px] mt-1.5" style={{ color: "var(--txt-m)" }}>Importance: <span style={{ color: "var(--txt)" }}>{(ins.importance * 100).toFixed(0)}%</span></p>
                  </div>
                ))}
              </div>
            ) : (!insightsLoading && !insightSummary && (
              <div className={`flex flex-col items-center justify-center py-16 ${styles.gc} rounded-2xl text-center`}>
                <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4" style={{ background: "rgba(99,102,241,.08)" }}>
                  <svg className="w-8 h-8" style={{ color: "#818cf8" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                </div>
                <p className="font-bold text-sm mb-1" style={{ color: "var(--txt)" }}>No insights yet</p>
                <p className="text-xs mb-4" style={{ color: "var(--txt-m)" }}>Upload a dataset, then click Run Insights</p>
              </div>
            ))}
          </div>
        )}

        {/* REPORTS TAB */}
        {activeTab === "reports" && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div><p className="font-bold" style={{ color: "var(--txt)" }}>Generated Reports</p><p className={`${styles.sl} mt-0.5`}>Automated HTML reporting engine</p></div>
              <button onClick={async () => {
                setReportLoading(true);
                const { ok, data, error } = await apiFetch("/reports/generate", { method: "POST" });
                setReportLoading(false);
                if (!ok) { pushToast({ type: "alert", icon: "❌", title: "Report failed", body: error }); return; }
                if (data && data.report_id) { setPreviewReportId(data.report_id); loadReports(); }
              }} disabled={reportLoading} className={styles.btnP}>
                <svg className={`w-4 h-4 ${reportLoading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24">
                  {reportLoading ? (
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  )}
                </svg>
                {reportLoading ? "Generating..." : "Generate Report"}
              </button>
            </div>
            {previewReportId && (
              <div className={`${styles.gc} rounded-2xl overflow-hidden`}>
                <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                  <p className="font-bold text-sm" style={{ color: "var(--txt)" }}>Report Preview</p>
                  <div className="flex gap-2">
                    <a href={`/api/reports/${previewReportId}`} target="_blank" rel="noreferrer" className={`${styles.btnS} text-[10px] py-1.5 px-3`}>
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                      Open Full
                    </a>
                    <a href={`/api/reports/${previewReportId}?format=pdf`} target="_blank" rel="noreferrer" className={`${styles.btnP} text-[10px] py-1.5 px-3`}>📄 Download PDF</a>
                  </div>
                </div>
                <iframe src={`/api/reports/${previewReportId}`} className="w-full rounded-b-2xl" style={{ height: "480px", border: 0, background: "#050505" }}></iframe>
              </div>
            )}
            <div className={`${styles.gc} rounded-2xl overflow-hidden`}>
              <div className="px-5 py-4 border-b" style={{ borderColor: "var(--border)" }}><p className="font-bold text-sm" style={{ color: "var(--txt)" }}>All Reports</p></div>
              {reports.length > 0 ? (
                <table className={styles.dt}>
                  <thead><tr><th>Dataset</th><th>Type</th><th>Created</th><th>Action</th></tr></thead>
                  <tbody>
                    {reports.map((r) => (
                      <tr key={r.id}>
                        <td className="font-medium" style={{ color: "var(--txt)" }}>{r.filename || "Dataset"}</td>
                        <td><span className={`${styles.badge} ${styles.badgeReport}`}>{r.triggered_by}</span></td>
                        <td style={{ color: "var(--txt-m)" }}>{timeAgo(r.created_at)}</td>
                        <td><button onClick={() => setPreviewReportId(r.id)} className={styles.badge} style={{ background: "rgba(46,91,255,.1)", color: "var(--accent)", border: "1px solid rgba(46,91,255,.2)" }}>Preview</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center"><p className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>No reports generated yet</p></div>
              )}
            </div>
          </div>
        )}

        {/* SCHEDULES TAB */}
        {activeTab === "schedules" && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div><p className="font-bold" style={{ color: "var(--txt)" }}>Report Schedules</p><p className={`${styles.sl} mt-0.5`}>Automated recurring report delivery</p></div>
              <button onClick={() => setShowNewSchedule(!showNewSchedule)} className={styles.btnP}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" /></svg>
                New Schedule
              </button>
            </div>
            {showNewSchedule && (
              <div className={`${styles.gc} rounded-2xl p-5 space-y-4`}>
                <p className="font-bold text-sm" style={{ color: "var(--txt)" }}>New Report Schedule</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className={styles.sl}>Frequency</label>
                    <select value={newSched.cron} onChange={(e) => { setNewSched({ ...newSched, cron: e.target.value }); setSchedErrors({ ...schedErrors, cron: V.cron(e.target.value) || "" }); }}
                      style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)", borderColor: schedErrors.cron ? "#ef4444" : undefined }}
                      className="w-full px-3 py-2 rounded-lg text-xs font-medium outline-none">
                      <option value="0 9 * * 1">Every Monday 9AM</option>
                      <option value="0 9 * * *">Every day 9AM</option>
                      <option value="0 9 1 * *">Monthly (1st)</option>
                      <option value="0 9 * * 1-5">Weekdays 9AM</option>
                    </select>
                    {schedErrors.cron && <p className="text-[10px] font-semibold" style={{ color: "#ef4444" }}>{schedErrors.cron}</p>}
                  </div>
                  <div className="space-y-1.5">
                    <label className={styles.sl}>Email <span style={{ color: "var(--txt-m)", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(optional)</span></label>
                    <input value={newSched.email} onChange={(e) => { setNewSched({ ...newSched, email: e.target.value }); if (schedErrors.email) setSchedErrors({ ...schedErrors, email: V.email(e.target.value) || "" }); }} onBlur={() => setSchedErrors({ ...schedErrors, email: V.email(newSched.email) || "" })}
                      style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)", borderColor: schedErrors.email ? "#ef4444" : undefined }}
                      type="email" placeholder="you@company.com" className="w-full px-3 py-2 rounded-lg text-xs outline-none" />
                    {schedErrors.email && <p className="text-[10px] font-semibold" style={{ color: "#ef4444" }}>{schedErrors.email}</p>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={async () => {
                    const cErr = V.cron(newSched.cron); const eErr = V.email(newSched.email);
                    setSchedErrors({ cron: cErr || "", email: eErr || "" });
                    if (cErr || eErr) return;
                    setSchedLoading(true);
                    const { ok, data, error } = await apiFetch("/schedules", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cron: newSched.cron.trim(), email: newSched.email.trim() }) });
                    setSchedLoading(false);
                    if (!ok) { pushToast({ type: "alert", icon: "❌", title: "Could not create schedule", body: error }); return; }
                    setShowNewSchedule(false); setNewSched({ cron: "0 9 * * 1", email: "" }); setSchedErrors({ cron: "", email: "" });
                    loadSchedules(); pushToast({ type: "info", icon: "📅", title: "Schedule created", body: data.cron_human });
                  }} disabled={schedLoading} className={styles.btnP}>{schedLoading ? "Creating..." : "Create Schedule"}</button>
                  <button onClick={() => { setShowNewSchedule(false); setSchedErrors({ cron: "", email: "" }); }} className={styles.btnS}>Cancel</button>
                </div>
              </div>
            )}
            {schedules.length > 0 ? (
              <div className={`${styles.gc} rounded-2xl overflow-hidden`}>
                <table className={styles.dt}>
                  <thead><tr><th>Dataset</th><th>Frequency</th><th>Email</th><th>Last Run</th><th></th></tr></thead>
                  <tbody>
                    {schedules.map((s) => (
                      <tr key={s.id}>
                        <td className="font-medium" style={{ color: "var(--txt)" }}>{s.filename || "Dataset"}</td>
                        <td><span className={`${styles.badge} ${styles.badgeInsights}`}>{s.cron_human}</span></td>
                        <td style={{ color: "var(--txt-m)" }}>{s.email || "—"}</td>
                        <td style={{ color: "var(--txt-m)" }}>{s.last_run ? timeAgo(s.last_run) : "Never"}</td>
                        <td><button onClick={async () => {
                          const { ok } = await apiFetch(`/schedules/${s.id}`, { method: "DELETE" });
                          if (ok) setSchedules(schedules.filter((x) => x.id !== s.id));
                        }} className={styles.badge} style={{ background: "rgba(239,68,68,.08)", color: "#ef4444", border: "1px solid rgba(239,68,68,.2)" }}>Delete</button></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (!showNewSchedule && (
              <div className={`flex flex-col items-center justify-center py-16 ${styles.gc} rounded-2xl text-center`}>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style={{ background: "rgba(46,91,255,.08)" }}>
                  <svg className="w-7 h-7" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </div>
                <p className="font-bold text-sm mb-1" style={{ color: "var(--txt)" }}>No schedules configured</p>
                <p className="text-xs mb-4" style={{ color: "var(--txt-m)" }}>Automate report delivery on a cadence</p>
              </div>
            ))}
          </div>
        )}

        {/* ALERTS TAB */}
        {activeTab === "alerts" && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div><p className="font-bold" style={{ color: "var(--txt)" }}>Data Alerts</p><p className={`${styles.sl} mt-0.5`}>Anomaly & threshold monitoring</p></div>
              <button onClick={checkAlerts} disabled={alertsChecking} className={styles.btnP}>
                <svg className={`w-4 h-4 ${alertsChecking ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24">
                  {alertsChecking ? (
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  )}
                </svg>
                {alertsChecking ? "Checking..." : "Check Now"}
              </button>
            </div>
            {alerts.length > 0 ? (
              <div className="space-y-3">
                {alerts.map((a) => (
                  <div key={a.id} className={`${styles.gc} rounded-xl p-4 flex items-start gap-4`}>
                    <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: a.severity === "critical" ? "rgba(239,68,68,.12)" : a.severity === "warning" ? "rgba(245,158,11,.12)" : "rgba(99,102,241,.12)" }}>
                      <svg className="w-4 h-4" style={{ color: a.severity === "critical" ? "#ef4444" : a.severity === "warning" ? "#fbbf24" : "#818cf8" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className={`${styles.badge} ${styles["sev" + a.severity.charAt(0).toUpperCase() + a.severity.slice(1)]}`}>{a.severity.toUpperCase()}</span>
                        <span className="text-[10px] font-bold" style={{ color: "var(--txt)" }}>{a.rule}</span>
                      </div>
                      <p className="text-xs" style={{ color: "var(--txt-m)" }}>{a.message}</p>
                      <p className="text-[10px] mt-1 opacity-60" style={{ color: "var(--txt-m)" }}>{a.filename || ""} · {timeAgo(a.triggered_at)}</p>
                    </div>
                    <button onClick={() => resolveAlert(a.id)} className={`${styles.btnS} text-[10px] py-1 px-2 flex-shrink-0`}>Resolve</button>
                  </div>
                ))}
              </div>
            ) : (
              <div className={`flex flex-col items-center justify-center py-16 ${styles.gc} rounded-2xl text-center`}>
                <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4" style={{ background: "rgba(16,185,129,.08)" }}>
                  <svg className="w-7 h-7" style={{ color: "#10b981" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                </div>
                <p className="font-bold text-sm mb-1" style={{ color: "var(--txt)" }}>All clear</p>
                <p className="text-xs" style={{ color: "var(--txt-m)" }}>No active alerts on your datasets</p>
              </div>
            )}
          </div>
        )}

        {/* ACCOUNT TAB */}
        {activeTab === "account" && (
          <div className="space-y-6">
            <div className={`${styles.gc} rounded-2xl p-6`}>
              <div className="flex items-center gap-3 mb-5">
                <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "rgba(46,91,255,.1)" }}>
                  <svg className="w-5 h-5" style={{ color: "var(--accent)" }} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                </div>
                <div><p className="font-bold text-sm" style={{ color: "var(--txt)" }}>My Account</p><p className={`${styles.sl} mt-0.5`}>Edit your profile name and avatar style</p></div>
              </div>

              <div className="flex flex-col sm:flex-row items-start gap-6">
                <div className="flex flex-col items-center gap-3 flex-shrink-0">
                  <div className="w-24 h-24 rounded-2xl overflow-hidden flex items-center justify-center relative" style={{ border: "2px solid var(--border)", background: "var(--surface)" }}>
                    {acct.avatarDataUri ? (
                      <img src={acct.avatarDataUri} className="w-full h-full object-cover" alt="Avatar" />
                    ) : avatarGenerating ? (
                      <div className="w-full h-full flex items-center justify-center" style={{ background: "var(--surface)" }}>
                        <svg className="w-6 h-6 animate-spin" style={{ color: "var(--accent)" }} fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
                      </div>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-3xl font-black" style={{ background: "var(--accent)", color: "#fff" }}>{(acct.name || "U")[0].toUpperCase()}</div>
                    )}
                  </div>
                  <button onClick={rerollAvatar} disabled={avatarGenerating} className="text-[10px] font-bold uppercase tracking-widest flex items-center gap-1 transition-opacity hover:opacity-70" style={{ color: "var(--accent)", background: "none", border: "none", cursor: "pointer", padding: 0 }}>
                    <svg className={`w-3 h-3 ${avatarGenerating ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    Re-roll
                  </button>
                  <p className="text-[9px] font-bold uppercase tracking-widest" style={{ color: "var(--txt-m)" }}>Avatar Preview</p>
                </div>

                <div className="flex-1 space-y-5 w-full">
                  <div className="space-y-1.5">
                    <label className={styles.sl}>Display Name</label>
                    <input value={acct.name} onChange={(e) => setAcct((prev: any) => ({ ...prev, name: e.target.value }))} onBlur={generateAvatar} type="text" placeholder="Your name" className="w-full px-3 py-2.5 rounded-lg text-sm outline-none transition-all" style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--txt)" }} />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <label className={styles.sl}>Avatar Style</label>
                      <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: "var(--accent)" }}>{acct.avatarStyle}</span>
                    </div>
                    <div className="grid grid-cols-5 sm:grid-cols-8 gap-1.5">
                      {avatarStyles.map((s) => (
                        <button key={s.id} onClick={() => selectStyle(s.id)} className={`flex flex-col items-center gap-1 p-1.5 rounded-xl border transition-all ${acct.avatarStyle === s.id ? "border-[var(--accent)] bg-[rgba(46,91,255,0.1)]" : "border-transparent hover:border-[var(--border)]"}`} title={s.label}>
                          <div className="w-8 h-8 rounded-lg overflow-hidden flex-shrink-0" style={{ background: "var(--surface)" }}>
                            {s.preview ? <img src={s.preview} className="w-full h-full object-cover" alt="" /> : <div className="w-full h-full flex items-center justify-center text-[8px] font-bold" style={{ color: "var(--txt-m)" }}>{s.label[0]}</div>}
                          </div>
                          <span className="text-[7px] font-bold truncate w-full text-center" style={{ color: "var(--txt-m)" }}>{s.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <button onClick={saveAccount} disabled={acctSaving} className={styles.btnP}>
                      <svg className={`w-4 h-4 ${acctSaving ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24">
                        {acctSaving ? (
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        ) : (
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                        )}
                      </svg>
                      {acctSaving ? "Saving..." : "Save Changes"}
                    </button>
                    {acctMsg && <p className="text-xs font-bold" style={{ color: acctMsgOk ? "#10b981" : "#ef4444" }}>{acctMsg}</p>}
                  </div>
                </div>
              </div>
            </div>
            {/* Cleaned Datasets */}
            <div className={`${styles.gc} rounded-2xl overflow-hidden`}>
              <div className="px-5 py-4 border-b flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                <div><p className="font-bold text-sm" style={{ color: "var(--txt)" }}>Cleaned Datasets</p></div>
                <span className={styles.badge} style={{ background: "rgba(16,185,129,.1)", color: "#10b981", border: "1px solid rgba(16,185,129,.25)" }}>{cleanedDatasets.filter((d) => d.has_clean).length} cleaned</span>
              </div>
              {acctDatasetsLoading ? (
                <div className="flex items-center justify-center py-10"><svg className="w-6 h-6 animate-spin" style={{ color: "var(--accent)" }} fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg></div>
              ) : cleanedDatasets.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className={styles.dt}>
                    <thead><tr><th>File</th><th>Src</th><th>Rows</th><th>Cols</th><th>Status</th><th>Action</th></tr></thead>
                    <tbody>
                      {cleanedDatasets.map((d: any) => (
                        <tr key={d.id}>
                          <td><span className="font-medium" style={{ color: "var(--txt)" }}>{d.filename}</span></td>
                          <td><span className={styles.badge} style={{ background: "rgba(46,91,255,.07)", color: "var(--txt-m)", border: "1px solid var(--border)" }}>{d.source_type || "csv"}</span></td>
                          <td className="font-mono">{d.rows}</td>
                          <td className="font-mono">{d.cols}</td>
                          <td>
                            {d.has_clean ? <span className={styles.badge} style={{ background: "rgba(16,185,129,.1)", color: "#10b981", border: "1px solid rgba(16,185,129,.25)" }}>Cleaned</span> : <span className={styles.badge} style={{ background: "rgba(255,255,255,.05)", color: "var(--txt-m)", border: "1px solid var(--border)" }}>Raw only</span>}
                          </td>
                          <td><Link href={`/workspace?upload_id=${d.id}`} className={styles.badge} style={{ background: "rgba(46,91,255,.1)", color: "var(--accent)", border: "1px solid rgba(46,91,255,.2)", textDecoration: "none" }}>Open</Link></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-xs font-bold mb-1" style={{ color: "var(--txt)" }}>No datasets yet</p>
                </div>
              )}
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <div className="max-w-6xl mx-auto px-4 md:px-6 pb-7 mt-4">
        <div className="flex items-center justify-between py-4 px-5 rounded-xl" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
          <div className="flex items-center gap-3">
            <svg className="w-4 h-4 flex-shrink-0" style={{ color: "#10b981" }} fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 4.946-3.078 9.141-7.404 10.825L10 18l-.596-.234C5.078 16.082 2 11.886 2 7.001c0-.682.057-1.35.166-2.002z" clipRule="evenodd" /></svg>
            <div>
              <p className="text-xs font-bold" style={{ color: "var(--txt)" }}>{user.email}</p>
              <p className={`${styles.sl} mt-0.5`}>Member since {initData?.member_since}</p>
            </div>
          </div>
          <a href="/api/logout" className="text-[10px] font-bold uppercase tracking-widest hover:opacity-70 transition-opacity" style={{ color: "#ef4444", textDecoration: "none" }}>Sign Out</a>
        </div>
      </div>
    </>
  );
}
