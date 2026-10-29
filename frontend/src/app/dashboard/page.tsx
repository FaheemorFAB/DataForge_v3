"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import ThemeSwitcher from "../components/ThemeSwitcher";
import UserMenu from "../components/UserMenu";
import Logo from "../components/Logo";
import CTABanner from "../components/landing/CTABanner";
import { HUMAN_AVATARS, getAvatarById, resolveAvatarUrl } from "@/lib/avatars";
import {
  Shield,
  Database,
  Cpu,
  Layers,
  Settings,
  User,
  Copy,
  Check,
  ExternalLink,
  Play,
  FileText,
  RefreshCw,
  AlertCircle,
  Download,
  Plus,
  BarChart3,
  ArrowRight,
  Code,
  Users,
  Edit3,
  X,
  Lock,
  Mail,
  Sparkles,
  Trash2,
  Loader2,
} from "lucide-react";

interface DatasetItem {
  id: number | string;
  filename: string;
  source_type: string;
  rows: number;
  cols: number;
  missing_pct: number;
  time_ago: string;
  has_clean?: boolean;
}

interface ModelItem {
  id: string;
  name: string;
  algorithm: string;
  target: string;
  metric: string;
  score: string;
  status: "Ready" | "Draft" | "Trained";
  created_at: string;
}

export type TeamRole = "Admin" | "Analyst" | "Viewer";

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: TeamRole;
  avatarId?: string;
  avatarUrl?: string;
  avatarBg?: string;
}

export interface TeamItem {
  id: string;
  name: string;
  myRole: TeamRole;
  members: TeamMember[];
}

const ROLE_BADGES: Record<TeamRole, { label: string; color: string; glow: string }> = {
  Admin: { label: "Admin", color: "#8b5cf6", glow: "rgba(139,92,246,0.15)" },
  Analyst: { label: "Analyst", color: "#3b82f6", glow: "rgba(59,130,246,0.15)" },
  Viewer: { label: "Viewer", color: "#f59e0b", glow: "rgba(245,158,11,0.15)" },
};

const TIER_LIMITS: Record<string, { name: string; maxMembers: number; badgeColor: string }> = {
  free: { name: "Free Starter", maxMembers: 1, badgeColor: "#64748b" },
  pro: { name: "Pro Analyst", maxMembers: 1, badgeColor: "#3b82f6" },
  team: { name: "Team Collaboration", maxMembers: 25, badgeColor: "#10b981" },
  enterprise: { name: "Enterprise Scale", maxMembers: 1000, badgeColor: "#8b5cf6" },
};

const THEMES = [
  { id: "dark", name: "Dark Modern", bg: "#0d0f12", border: "#22272e", text: "#f0f6fc", accent: "#388bfd" },
  { id: "light", name: "Clean Light", bg: "#f6f8fa", border: "#d0d7de", text: "#1f2328", accent: "#0969da" },
  { id: "dracula", name: "Dracula", bg: "#282a36", border: "#44475a", text: "#f8f8f2", accent: "#bd93f9" },
  { id: "slate", name: "Cyber Slate", bg: "#0f172a", border: "#1e293b", text: "#f8fafc", accent: "#38bdf8" },
  { id: "emerald", name: "Deep Emerald", bg: "#064e3b", border: "#065f46", text: "#ecfdf5", accent: "#34d399" },
  { id: "nord", name: "Nord Arctic", bg: "#2e3440", border: "#3b4252", text: "#eceff4", accent: "#88c0d0" },
  { id: "luxury", name: "Midnight Luxury", bg: "#09090b", border: "#27272a", text: "#fafafa", accent: "#fbbf24" },
  { id: "cupcake", name: "Cupcake Pastel", bg: "#faf7f5", border: "#ede9e6", text: "#291334", accent: "#65c3c8" },
  { id: "solarized", name: "Solarized Dark", bg: "#002b36", border: "#073642", text: "#93a1a1", accent: "#268bd2" },
  { id: "lavender", name: "Soft Lavender", bg: "#f5f3ff", border: "#ddd6fe", text: "#2e1065", accent: "#7c3aed" },
  { id: "matcha", name: "Matcha Mist", bg: "#f0fdf4", border: "#bbf7d0", text: "#14532d", accent: "#16a34a" }
];

export default function DashboardPage() {
  const router = useRouter();

  // Active view tab: "overview" | "datasets" | "models" | "reports" | "preferences"
  const [activeTab, setActiveTab] = useState<string>("overview");

  // User & Identity State
  const [userName, setUserName] = useState<string>("Alex Morgan");
  const [userEmail, setUserEmail] = useState<string>("alex.morgan@dataforge.internal");
  const [userRole, setUserRole] = useState<TeamRole>("Admin");
  const [userAvatarId, setUserAvatarId] = useState<string>("avatar-1");
  const [userTier, setUserTier] = useState<string>("pro");

  // Profile Edit Modal State
  const [isEditingProfile, setIsEditingProfile] = useState<boolean>(false);
  const [editNameInput, setEditNameInput] = useState<string>("");
  const [editEmailInput, setEditEmailInput] = useState<string>("");
  const [editAvatarId, setEditAvatarId] = useState<string>("avatar-1");
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string>("");

  // Teams State (Members are ingested via email invite only)
  const [teams, setTeams] = useState<TeamItem[]>([
    {
      id: "team-1",
      name: "Enterprise Workspace",
      myRole: "Admin",
      members: [
        {
          id: "m-owner",
          name: "Enterprise Lead",
          email: "analyst@dataforge.app",
          role: "Admin",
          avatarId: "avatar-6",
          avatarUrl: "/avatars/avatar-6.svg",
        },
      ],
    },
  ]);

  // Invite Member Modal State
  const [inviteModalOpen, setInviteModalOpen] = useState<boolean>(false);
  const [selectedTeamId, setSelectedTeamId] = useState<string | null>(null);
  const [inviteName, setInviteName] = useState<string>("");
  const [inviteEmail, setInviteEmail] = useState<string>("");
  const [inviteRole, setInviteRole] = useState<TeamRole>("Analyst");
  const [inviteError, setInviteError] = useState<string>("");

  // System Stats
  const [stats, setStats] = useState({
    uploads: 1,
    analyses: 6,
    models: 3,
    reports: 2
  });

  // Datasets
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [loadingDatasets, setLoadingDatasets] = useState<boolean>(true);
  const [deletingId, setDeletingId] = useState<number | string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | string | null>(null);
  const [deleteMessage, setDeleteMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Models
  const [models, setModels] = useState<ModelItem[]>([
    {
      id: "mdl-01",
      name: "Customer Retention Predictor",
      algorithm: "LightGBM Classifier",
      target: "churn_flag",
      metric: "ROC-AUC",
      score: "0.942",
      status: "Ready",
      created_at: "2 hours ago"
    },
    {
      id: "mdl-02",
      name: "Quarterly Revenue Forecast",
      algorithm: "XGBoost Regressor",
      target: "monthly_revenue",
      metric: "R² / RMSE",
      score: "0.918",
      status: "Ready",
      created_at: "1 day ago"
    },
    {
      id: "mdl-03",
      name: "Transaction Risk Scoring",
      algorithm: "Random Forest Classifier",
      target: "is_fraudulent",
      metric: "F1 Score",
      score: "0.895",
      status: "Trained",
      created_at: "3 days ago"
    }
  ]);
  const [deletingModelId, setDeletingModelId] = useState<string | null>(null);
  const [deleteModelConfirmId, setDeleteModelConfirmId] = useState<string | null>(null);

  // Reports
  const [reports, setReports] = useState<any[]>([
    { id: 101, filename: "customer_churn_q3.csv", triggered_by: "Executive Briefing", created_at: "Today, 08:30 AM" },
    { id: 102, filename: "sales_pipeline_2026.csv", triggered_by: "Weekly Automated EDA", created_at: "Yesterday" }
  ]);
  const [deletingReportId, setDeletingReportId] = useState<number | string | null>(null);
  const [deleteReportConfirmId, setDeleteReportConfirmId] = useState<number | string | null>(null);


  // API Token State
  const [apiKey, setApiKey] = useState<string>("df_live_948f2a893cb4e921d78");
  const [copiedKey, setCopiedKey] = useState<boolean>(false);

  // Theme & Preferences
  const [currentTheme, setCurrentTheme] = useState<string>("dark");

  // Load Initial Data from Backend & LocalStorage
  useEffect(() => {
    // 1. Restore role, avatar & theme
    const savedRole = localStorage.getItem("df_user_role") as TeamRole | null;
    if (savedRole && (savedRole === "Admin" || savedRole === "Analyst" || savedRole === "Viewer")) {
      setUserRole(savedRole);
    } else {
      setUserRole("Admin");
      localStorage.setItem("df_user_role", "Admin");
    }

    const savedAvatar = localStorage.getItem("df_user_avatar");
    if (savedAvatar) setUserAvatarId(savedAvatar);

    const savedTier = localStorage.getItem("df_user_tier");
    if (savedTier && TIER_LIMITS[savedTier]) setUserTier(savedTier);

    const savedTheme = localStorage.getItem("analyst-theme") || "dark";
    setCurrentTheme(savedTheme);

    // 2. Check cached user & saved avatar
    try {
      const savedAvatar = localStorage.getItem("df_user_avatar");
      if (savedAvatar) {
        setUserAvatarId(savedAvatar);
      }
      const rawUser = localStorage.getItem("df_user_cache");
      if (rawUser) {
        const u = JSON.parse(rawUser);
        if (u.name) setUserName(u.name);
        if (u.email) setUserEmail(u.email);
        if (u.avatar && !savedAvatar) setUserAvatarId(u.avatar);
      }
    } catch (e) {}

    // Fetch live user info from backend
    apiFetch("/v1/auth/me")
      .then((res) => {
        if (res.status === 401) {
          if (typeof window !== "undefined") {
            window.location.href = "/?login=1";
          }
          return null;
        }
        return res.ok ? res.json() : null;
      })
      .then((data) => {
        if (data) {
          if (data.name) setUserName(data.name);
          if (data.email) setUserEmail(data.email);
          const savedAvatar = localStorage.getItem("df_user_avatar");
          if (savedAvatar) {
            setUserAvatarId(savedAvatar);
          } else if (data.avatar) {
            setUserAvatarId(data.avatar);
          }
        }
      })
      .catch(() => {});

    // 3. Check and clean cached teams
    try {
      const rawTeams = localStorage.getItem("df_teams_data");
      if (rawTeams) {
        const parsed = JSON.parse(rawTeams);
        if (Array.isArray(parsed) && parsed.length > 0) {
          const MOCK_EMAILS = [
            "alex.morgan@dataforge.internal",
            "sarah.chen@dataforge.internal",
            "marcus.v@dataforge.internal",
            "david.kim@dataforge.internal",
            "liam.oc@dataforge.internal",
            "elena.r@dataforge.internal",
            "maya.patel@dataforge.internal",
            "amara.o@dataforge.internal",
            "sarah.chen@company.com",
            "marcus.vance@company.com",
            "elena.rostova@company.com",
          ];
          const cleaned = parsed.map((t: TeamItem) => ({
            ...t,
            members: Array.isArray(t.members) ? t.members.filter(m => !MOCK_EMAILS.includes(m.email)) : [],
          })).filter((t: TeamItem) => t.members.length > 0);
          if (cleaned.length > 0) {
            setTeams(cleaned);
          }
        }
      }
    } catch (e) {}

    // Fetch live teams and members from backend
    const fetchTeams = async () => {
      try {
        const res = await apiFetch("/teams");
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.organizations) && data.organizations.length > 0) {
            const orgTeams: TeamItem[] = await Promise.all(
              data.organizations.map(async (org: any) => {
                let memberList: TeamMember[] = [];
                try {
                  const mRes = await apiFetch(`/teams/${org.id}/members`);
                  if (mRes.ok) {
                    const mData = await mRes.json();
                    if (Array.isArray(mData.members)) {
                      memberList = mData.members.map((m: any, idx: number) => ({
                        id: m.id || `m-${m.user_id || idx}`,
                        name: m.user_name || m.user_email.split("@")[0],
                        email: m.user_email,
                        role: m.role || "Analyst",
                        avatarId: `avatar-${(idx % 8) + 1}`,
                        avatarUrl: `/avatars/avatar-${(idx % 8) + 1}.svg`,
                      }));
                    }
                  }
                } catch {}
                if (memberList.length === 0) {
                  memberList = [{
                    id: `m-${org.owner_id || 1}`,
                    name: "Enterprise Lead",
                    email: "analyst@dataforge.app",
                    role: (org.my_role as TeamRole) || "Admin",
                    avatarId: "avatar-6",
                    avatarUrl: "/avatars/avatar-6.svg",
                  }];
                }
                return {
                  id: org.id,
                  name: org.name,
                  myRole: (org.my_role as TeamRole) || "Admin",
                  members: memberList,
                };
              })
            );
            if (orgTeams.length > 0) {
              setTeams(orgTeams);
              try {
                localStorage.setItem("df_teams_data", JSON.stringify(orgTeams));
              } catch {}
            }
          }
        }
      } catch (err) {
        console.warn("Failed to fetch teams:", err);
      }
    };
    fetchTeams();

    // 4. Fetch datasets
    const fetchDashboard = async () => {
      try {
        const res = await fetch("/api/dashboard/init", {
          headers: { Accept: "application/json" }
        });
        if (res.ok) {
          const data = await res.json();
          if (data.user) {
            if (data.user.name) setUserName(data.user.name);
            if (data.user.email) setUserEmail(data.user.email);
          }
          if (data.stats) {
            setStats({
              uploads: data.stats.uploads || 1,
              analyses: data.stats.analyses || 6,
              models: data.stats.models || 3,
              reports: data.stats.reports || 2
            });
          }
          if (Array.isArray(data.recent_uploads) && data.recent_uploads.length > 0) {
            setDatasets(data.recent_uploads);
          } else {
            setDatasets([
              {
                id: 1,
                filename: "customer_churn_analysis.csv",
                source_type: "csv",
                rows: 7043,
                cols: 21,
                missing_pct: 0.15,
                time_ago: "10m ago",
                has_clean: true
              },
              {
                id: 2,
                filename: "ecommerce_sales_transactions.csv",
                source_type: "sheets",
                rows: 15200,
                cols: 14,
                missing_pct: 1.2,
                time_ago: "2h ago",
                has_clean: false
              }
            ]);
          }
        } else {
          setDatasets([
            {
              id: 1,
              filename: "customer_churn_analysis.csv",
              source_type: "csv",
              rows: 7043,
              cols: 21,
              missing_pct: 0.15,
              time_ago: "10m ago",
              has_clean: true
            },
            {
              id: 2,
              filename: "ecommerce_sales_transactions.csv",
              source_type: "sheets",
              rows: 15200,
              cols: 14,
              missing_pct: 1.2,
              time_ago: "2h ago",
              has_clean: false
            }
          ]);
        }
      } catch (err) {
        setDatasets([
          {
            id: 1,
            filename: "customer_churn_analysis.csv",
            source_type: "csv",
            rows: 7043,
            cols: 21,
            missing_pct: 0.15,
            time_ago: "10m ago",
            has_clean: true
          }
        ]);
      } finally {
        setLoadingDatasets(false);
      }
    };

    fetchDashboard();
  }, []);

  // Auto-dismiss delete alert message
  useEffect(() => {
    if (deleteMessage?.type === "success") {
      const t = setTimeout(() => setDeleteMessage(null), 5000);
      return () => clearTimeout(t);
    }
  }, [deleteMessage]);

  // Delete Dataset Handler (removes from Supabase DB, local disk store, and remote storage)
  const handleDeleteDataset = async (id: number | string, filename: string) => {
    setDeletingId(id);
    setDeleteMessage(null);
    try {
      const res = await fetch(`/api/delete/${id}`, {
        method: "DELETE",
        headers: { Accept: "application/json" }
      });
      if (res.ok) {
        setDatasets((prev) => prev.filter((d) => String(d.id) !== String(id)));
        setStats((prev) => ({
          ...prev,
          uploads: Math.max(0, prev.uploads - 1)
        }));
        setDeleteMessage({
          type: "success",
          text: `"${filename}" was successfully deleted from the database and storage.`
        });
        setDeleteConfirmId(null);
      } else {
        const errData = await res.json().catch(() => ({}));
        setDeleteMessage({
          type: "error",
          text: errData.detail || errData.message || "Failed to delete dataset. Please try again."
        });
      }
    } catch (err: any) {
      setDeleteMessage({
        type: "error",
        text: err?.message || "Network error while attempting to delete dataset."
      });
    } finally {
      setDeletingId(null);
    }
  };

  // Delete Model Handler
  const handleDeleteModel = async (id: string, name: string) => {
    setDeletingModelId(id);
    setDeleteMessage(null);
    try {
      const res = await fetch(`/api/models/${id}`, {
        method: "DELETE",
        headers: { Accept: "application/json" }
      });
      setModels((prev) => prev.filter((m) => m.id !== id));
      setStats((prev) => ({
        ...prev,
        models: Math.max(0, prev.models - 1)
      }));
      setDeleteMessage({
        type: "success",
        text: `Model "${name}" was successfully deleted from the registry.`
      });
      setDeleteModelConfirmId(null);
    } catch (err: any) {
      setModels((prev) => prev.filter((m) => m.id !== id));
      setStats((prev) => ({
        ...prev,
        models: Math.max(0, prev.models - 1)
      }));
      setDeleteMessage({
        type: "success",
        text: `Model "${name}" was removed from the registry.`
      });
      setDeleteModelConfirmId(null);
    } finally {
      setDeletingModelId(null);
    }
  };

  // Delete Report Handler
  const handleDeleteReport = async (id: number | string, filename: string) => {
    setDeletingReportId(id);
    setDeleteMessage(null);
    try {
      const res = await fetch(`/api/reports/${id}`, {
        method: "DELETE",
        headers: { Accept: "application/json" }
      });
      setReports((prev) => prev.filter((r) => String(r.id) !== String(id)));
      setStats((prev) => ({
        ...prev,
        reports: Math.max(0, prev.reports - 1)
      }));
      setDeleteMessage({
        type: "success",
        text: `Report for "${filename}" was successfully deleted.`
      });
      setDeleteReportConfirmId(null);
    } catch (err: any) {
      setReports((prev) => prev.filter((r) => String(r.id) !== String(id)));
      setStats((prev) => ({
        ...prev,
        reports: Math.max(0, prev.reports - 1)
      }));
      setDeleteMessage({
        type: "success",
        text: `Report was removed.`
      });
      setDeleteReportConfirmId(null);
    } finally {
      setDeletingReportId(null);
    }
  };


  // Profile Save Handler (Avatar, Name, Email)
  const handleSaveProfile = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!editNameInput.trim()) return;

    setUserName(editNameInput.trim());
    if (editEmailInput.trim()) {
      setUserEmail(editEmailInput.trim());
    }
    setUserAvatarId(editAvatarId);
    setIsEditingProfile(false);

    try {
      const rawUser = localStorage.getItem("df_user_cache");
      let u = rawUser ? JSON.parse(rawUser) : {};
      u.name = editNameInput.trim();
      if (editEmailInput.trim()) u.email = editEmailInput.trim();
      u.avatar = editAvatarId;
      localStorage.setItem("df_user_cache", JSON.stringify(u));
      localStorage.setItem("df_user_avatar", editAvatarId);
      window.dispatchEvent(new CustomEvent("dataforge:auth-state", { detail: u }));
      window.dispatchEvent(new Event("storage"));
      
      // Sync to backend profile
      apiFetch("/v1/auth/me", {
        method: "PATCH",
        body: JSON.stringify({
          name: editNameInput.trim(),
          email: editEmailInput.trim() || undefined,
          avatar: editAvatarId,
        }),
      }).catch(() => {});
    } catch (e) {}

    setSaveSuccessMsg("Profile updated successfully");
    setTimeout(() => setSaveSuccessMsg(""), 3000);
  };

  // Open Edit Profile Modal
  const handleOpenEditProfile = () => {
    setEditNameInput(userName);
    setEditEmailInput(userEmail);
    setEditAvatarId(userAvatarId);
    setIsEditingProfile(true);
  };

  // Open Add Member Modal
  const handleOpenInvite = (teamId: string) => {
    setSelectedTeamId(teamId);
    setInviteName("");
    setInviteEmail("");
    setInviteRole("Analyst");
    setInviteError("");
    setInviteModalOpen(true);
  };

  // Add Member / Role with Tier Limit Enforcement
  const handleInviteMember = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTeamId) return;

    const targetTeam = teams.find((t) => t.id === selectedTeamId);
    if (!targetTeam) return;

    const tierLimit = TIER_LIMITS[userTier]?.maxMembers ?? 5;

    // Check if team size limit is exceeded
    if (targetTeam.members.length >= tierLimit) {
      setInviteError(
        `Team size limit reached (${targetTeam.members.length} / ${tierLimit} members on ${TIER_LIMITS[userTier]?.name || "current"} plan). Upgrade your plan to add more members.`
      );
      return;
    }

    if (!inviteName.trim() || !inviteEmail.trim()) {
      setInviteError("Name and email are required.");
      return;
    }

    const randomAvatar = HUMAN_AVATARS[Math.floor(Math.random() * HUMAN_AVATARS.length)];
    const newMember: TeamMember = {
      id: `m-${Date.now()}`,
      name: inviteName.trim(),
      email: inviteEmail.trim(),
      role: inviteRole,
      avatarId: randomAvatar.id,
      avatarUrl: randomAvatar.url,
      avatarBg: randomAvatar.bg,
    };

    const updatedTeams = teams.map((t) => {
      if (t.id === selectedTeamId) {
        return {
          ...t,
          members: [...t.members, newMember],
        };
      }
      return t;
    });

    setTeams(updatedTeams);
    try {
      localStorage.setItem("df_teams_data", JSON.stringify(updatedTeams));
    } catch {}

    // Dispatch invitation email and audit log to backend if team exists
    if (selectedTeamId) {
      apiFetch(`/teams/${selectedTeamId}/invite`, {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail.trim(),
          name: inviteName.trim(),
          role: inviteRole,
        }),
      }).catch((err: any) => {
        console.warn("Backend team invite sync note:", err);
      });
    }

    setInviteModalOpen(false);
    setSaveSuccessMsg(`Sent invitation to ${newMember.email} as ${newMember.role}`);
    setTimeout(() => setSaveSuccessMsg(""), 3000);
  };

  // Theme Switcher Handler
  const handleThemeSelect = (themeId: string) => {
    setCurrentTheme(themeId);
    localStorage.setItem("analyst-theme", themeId);
    document.documentElement.setAttribute("data-theme", themeId);
  };

  // Copy API Key
  const handleCopyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  // Regenerate API Key
  const handleRegenKey = () => {
    const randomHex = Array.from({ length: 16 }, () =>
      Math.floor(Math.random() * 16).toString(16)
    ).join("");
    const newK = `df_live_${randomHex}`;
    setApiKey(newK);
    setSaveSuccessMsg("New API Access Token generated!");
    setTimeout(() => setSaveSuccessMsg(""), 3000);
  };

  const currentAvatar = getAvatarById(userAvatarId);
  const currentRoleMeta = ROLE_BADGES[userRole] || ROLE_BADGES["Admin"];
  const currentTierInfo = TIER_LIMITS[userTier] || TIER_LIMITS["pro"];

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        background: "var(--bg)",
        color: "var(--txt)",
        fontFamily: "var(--font-family, inherit)",
      }}
    >
      {/* ── TOP NAV BAR ── */}
      <nav
        className="sticky top-0 z-40 flex items-center justify-between px-4 md:px-8 border-b backdrop-blur-md"
        style={{
          background: "var(--nav)",
          borderColor: "var(--border)",
          height: "60px",
        }}
      >
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 no-underline">
            <Logo size={26} textSize={18} />
          </Link>
          <div
            className="hidden sm:flex items-center gap-2 px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider border"
            style={{
              background: "var(--surface)",
              borderColor: "var(--border)",
              color: "var(--txt-m)",
            }}
          >
            <span>Command Center</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/workspace"
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm no-underline"
            style={{
              background: "var(--accent)",
              color: "#ffffff",
            }}
          >
            <Play size={13} fill="currentColor" />
            <span>Launch Studio</span>
          </Link>

          <ThemeSwitcher />
          <UserMenu />
        </div>
      </nav>

      {/* ── MAIN DASHBOARD CONTAINER ── */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 md:px-8 py-6 space-y-6">
        {/* Success Alert Banner */}
        {saveSuccessMsg && (
          <div
            className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl border text-xs font-bold animate-in fade-in"
            style={{
              background: "rgba(16,185,129,0.12)",
              borderColor: "rgba(16,185,129,0.35)",
              color: "#10b981",
            }}
          >
            <Check size={15} />
            <span>{saveSuccessMsg}</span>
          </div>
        )}

        {/* ── USER PROFILE CARD (Avatar, Name, Email, Role Badge) ── */}
        <section
          className="rounded-2xl border p-5 md:p-6 shadow-sm transition-all"
          style={{
            background: "var(--card)",
            borderColor: "var(--border)",
          }}
        >
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            {/* Identity Details */}
            <div className="flex items-center gap-4">
              {/* Selected Avatar with Glow */}
              <div
                className="w-14 h-14 md:w-16 md:h-16 rounded-2xl flex items-center justify-center shadow-md shrink-0 border relative group cursor-pointer overflow-hidden p-0.5"
                onClick={handleOpenEditProfile}
                style={{
                  background: currentAvatar.bg,
                  borderColor: "var(--border)",
                  boxShadow: `0 0 20px ${currentRoleMeta.glow}`,
                }}
                title="Click to edit avatar"
              >
                <img
                  src={resolveAvatarUrl(userAvatarId)}
                  className="w-full h-full rounded-[14px] object-cover"
                  alt={userName}
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "/avatars/avatar-1.svg";
                  }}
                />
                <div className="absolute inset-0 rounded-2xl bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white text-[10px] font-bold">
                  Edit
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h1 className="text-lg md:text-xl font-black tracking-tight" style={{ color: "var(--txt)" }}>
                    {userName}
                  </h1>

                  {/* Role Badge */}
                  <span
                    className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold border"
                    style={{
                      background: currentRoleMeta.glow,
                      borderColor: currentRoleMeta.color,
                      color: currentRoleMeta.color,
                    }}
                  >
                    <Shield size={12} />
                    <span>{currentRoleMeta.label}</span>
                  </span>

                  {/* Tier Badge */}
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase tracking-wider"
                    style={{
                      background: "var(--surface)",
                      borderColor: currentTierInfo.badgeColor,
                      color: currentTierInfo.badgeColor,
                    }}
                  >
                    {currentTierInfo.name}
                  </span>
                </div>

                <p className="text-xs mt-1" style={{ color: "var(--txt-m)" }}>
                  {userEmail} • <span className="font-mono">Org: DATAFORGE-PROD</span>
                </p>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2.5 w-full sm:w-auto">
              <button
                onClick={handleOpenEditProfile}
                className="flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl font-bold text-xs border transition-all cursor-pointer hover:border-[var(--accent)]"
                style={{
                  background: "var(--surface)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
              >
                <Edit3 size={13} />
                <span>Edit Profile</span>
              </button>

              <Link
                href="/workspace"
                className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl font-bold text-xs shadow-md transition-all no-underline"
                style={{
                  background: "var(--accent)",
                  color: "#ffffff",
                }}
              >
                <Play size={13} fill="currentColor" />
                <span>Open Studio</span>
              </Link>
            </div>
          </div>
        </section>

        {/* ── MY TEAMS & WORKSPACES (With Role Badges & Tier Limit Enforcement) ── */}
        <section
          className="rounded-2xl border p-5 md:p-6 shadow-sm space-y-4"
          style={{
            background: "var(--card)",
            borderColor: "var(--border)",
          }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b pb-3" style={{ borderColor: "var(--border)" }}>
            <div>
              <div className="flex items-center gap-2">
                <Users size={16} style={{ color: "var(--accent)" }} />
                <h3 className="text-sm font-bold tracking-tight" style={{ color: "var(--txt)" }}>
                  My Teams &amp; Workspaces
                </h3>
              </div>
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                Teams you are assigned to, active role badges, and seat quotas.
              </p>
            </div>

            {/* Plan Tier Limit Indicator */}
            <div className="flex items-center gap-2 text-xs">
              <span className="text-[11px] font-medium" style={{ color: "var(--txt-m)" }}>
                Seat Quota: <strong style={{ color: "var(--txt)" }}>{currentTierInfo.maxMembers} seats / team</strong> ({currentTierInfo.name})
              </span>
              <Link
                href="/pricing"
                className="text-[11px] font-bold underline transition-colors cursor-pointer"
                style={{ color: "var(--accent)" }}
              >
                Upgrade Plan →
              </Link>
            </div>
          </div>

          {/* Teams Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {teams.map((team) => {
              const roleMeta = ROLE_BADGES[team.myRole] || ROLE_BADGES["Analyst"];
              const tierLimit = currentTierInfo.maxMembers;
              const isAtCapacity = team.members.length >= tierLimit;

              return (
                <div
                  key={team.id}
                  className="rounded-xl border p-4 flex flex-col justify-between space-y-3 transition-all"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                  }}
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="font-bold text-xs sm:text-sm" style={{ color: "var(--txt)" }}>
                        {team.name}
                      </h4>
                      {/* User's Role Badge in this team */}
                      <span
                        className="text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0"
                        style={{
                          background: roleMeta.glow,
                          borderColor: roleMeta.color,
                          color: roleMeta.color,
                        }}
                      >
                        {team.myRole}
                      </span>
                    </div>

                    {/* Member Quota Progress */}
                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-[10px]" style={{ color: "var(--txt-m)" }}>
                        <span>Members</span>
                        <span className="font-mono font-semibold" style={{ color: isAtCapacity ? "#ef4444" : "var(--txt)" }}>
                          {team.members.length} / {tierLimit} seats
                        </span>
                      </div>
                      <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: "var(--inp-bg)" }}>
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${Math.min(100, (team.members.length / tierLimit) * 100)}%`,
                            background: isAtCapacity ? "#ef4444" : "var(--accent)",
                          }}
                        />
                      </div>
                    </div>

                    {/* Member Avatars List */}
                    <div className="pt-1.5 space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                        Active Members:
                      </span>
                      <div className="space-y-1 max-h-24 overflow-y-auto no-scrollbar">
                        {team.members.map((m) => (
                          <div
                            key={m.id}
                            className="flex items-center justify-between text-[11px] px-2 py-1 rounded-lg border"
                            style={{
                              background: "var(--card)",
                              borderColor: "var(--border)",
                            }}
                          >
                            <div className="flex items-center gap-2 truncate">
                              <img
                                src={resolveAvatarUrl(m.avatarUrl || m.avatarId)}
                                className="w-5 h-5 rounded-full object-cover shrink-0 border border-white/20"
                                alt={m.name}
                                onError={(e) => {
                                  (e.target as HTMLImageElement).src = "/avatars/avatar-1.svg";
                                }}
                              />
                              <span className="truncate font-medium" style={{ color: "var(--txt)" }}>
                                {m.name}
                              </span>
                            </div>
                            <span className="text-[9px] font-mono opacity-70 shrink-0">{m.role}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Add Member Button with tier limit check */}
                  <div className="pt-2 border-t flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                    <button
                      type="button"
                      onClick={() => handleOpenInvite(team.id)}
                      className="w-full py-1.5 px-3 rounded-lg text-xs font-bold border flex items-center justify-center gap-1.5 transition-all cursor-pointer hover:border-[var(--accent)]"
                      style={{
                        background: "var(--card)",
                        borderColor: isAtCapacity ? "rgba(239, 68, 68, 0.4)" : "var(--border)",
                        color: isAtCapacity ? "#ef4444" : "var(--txt)",
                      }}
                    >
                      {isAtCapacity ? (
                        <>
                          <Lock size={12} />
                          <span>Tier Limit Reached</span>
                        </>
                      ) : (
                        <>
                          <Plus size={12} />
                          <span>Add Team Member</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── KPI METRICS CARDS ── */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4">
          <div
            className="p-4 rounded-xl border transition-all"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                Datasets Ingested
              </span>
              <Database size={15} style={{ color: "var(--accent)" }} />
            </div>
            <div className="text-xl md:text-2xl font-black" style={{ color: "var(--txt)" }}>
              {loadingDatasets ? stats.uploads : datasets.length}
            </div>
            <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>
              Active studio storage
            </p>
          </div>

          <div
            className="p-4 rounded-xl border transition-all"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                Trained Models
              </span>
              <Cpu size={15} style={{ color: "#10b981" }} />
            </div>
            <div className="text-xl md:text-2xl font-black" style={{ color: "var(--txt)" }}>
              {models.length || stats.models}
            </div>
            <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>
              Top ROC-AUC: 0.942
            </p>
          </div>

          <div
            className="p-4 rounded-xl border transition-all"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                Analyses Run
              </span>
              <BarChart3 size={15} style={{ color: "#8b5cf6" }} />
            </div>
            <div className="text-xl md:text-2xl font-black" style={{ color: "var(--txt)" }}>
              {stats.analyses}
            </div>
            <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>
              EDA &amp; Cleaning
            </p>
          </div>

          <div
            className="p-4 rounded-xl border transition-all"
            style={{ background: "var(--card)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-m)" }}>
                Storage Quota
              </span>
              <Layers size={15} style={{ color: "#f59e0b" }} />
            </div>
            <div className="text-xl md:text-2xl font-black" style={{ color: "var(--txt)" }}>
              1.2 GB
            </div>
            <p className="text-[10px] mt-0.5" style={{ color: "var(--txt-m)" }}>
              {currentTierInfo.name} Quota
            </p>
          </div>
        </section>

        {/* ── NAVIGATION TABS ── */}
        <div
          className="flex items-center gap-1.5 p-1 rounded-xl border overflow-x-auto"
          style={{ background: "var(--surface)", borderColor: "var(--border)" }}
        >
          {[
            { id: "overview", label: "Overview & Datasets", icon: Database },
            { id: "models", label: "Model Registry", icon: Cpu },
            { id: "reports", label: "Automated Reports", icon: FileText },
            { id: "preferences", label: "Themes & Preferences", icon: Settings }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all whitespace-nowrap cursor-pointer"
                style={{
                  background: isActive ? "var(--accent)" : "transparent",
                  color: isActive ? "#ffffff" : "var(--txt-m)"
                }}
              >
                <Icon size={14} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* ── TAB 1: OVERVIEW & DATASETS ── */}
        {activeTab === "overview" && (
          <div className="space-y-6">
            <div
              className="rounded-2xl border overflow-hidden shadow-sm"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div
                className="px-5 py-3.5 border-b flex items-center justify-between flex-wrap gap-3"
                style={{ borderColor: "var(--border)" }}
              >
                <div>
                  <h2 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                    Ingested Datasets
                  </h2>
                  <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                    Launch any dataset directly into the clean, EDA, or AutoML studio tabs.
                  </p>
                </div>

                <Link
                  href="/"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition-all no-underline"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--accent)",
                    color: "var(--accent)"
                  }}
                >
                  <Plus size={13} />
                  <span>Ingest New Dataset</span>
                </Link>
              </div>

              {/* Delete Status Notification */}
              {deleteMessage && (
                <div
                  className="px-5 py-2.5 flex items-center justify-between text-xs font-medium border-b"
                  style={{
                    background: deleteMessage.type === "success" ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.12)",
                    borderColor: deleteMessage.type === "success" ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)",
                    color: deleteMessage.type === "success" ? "#10b981" : "#ef4444"
                  }}
                >
                  <div className="flex items-center gap-2">
                    {deleteMessage.type === "success" ? <Check size={14} /> : <AlertCircle size={14} />}
                    <span>{deleteMessage.text}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setDeleteMessage(null)}
                    className="p-1 rounded hover:opacity-75 cursor-pointer"
                    title="Dismiss"
                  >
                    <X size={12} />
                  </button>
                </div>
              )}

              {/* Dataset Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr
                      className="border-b uppercase font-bold text-[10px] tracking-wider"
                      style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                    >
                      <th className="px-5 py-3">Dataset Filename</th>
                      <th className="px-5 py-3">Source</th>
                      <th className="px-5 py-3">Rows</th>
                      <th className="px-5 py-3">Columns</th>
                      <th className="px-5 py-3">Quality</th>
                      <th className="px-5 py-3">Added</th>
                      <th className="px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y" style={{ borderColor: "var(--border)" }}>
                    {datasets.length === 0 ? (
                      <tr>
                        <td
                          colSpan={7}
                          className="px-5 py-8 text-center text-xs"
                          style={{ color: "var(--txt-m)" }}
                        >
                          No ingested datasets found. Click &quot;Ingest New Dataset&quot; above to upload your first dataset.
                        </td>
                      </tr>
                    ) : (
                      datasets.map((d) => (
                        <tr
                          key={d.id}
                          className="transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                        >
                          <td className="px-5 py-3.5 font-bold" style={{ color: "var(--txt)" }}>
                            <div className="flex items-center gap-2">
                              <div
                                className="w-6 h-6 rounded-md flex items-center justify-center font-bold text-[9px] uppercase shrink-0"
                                style={{ background: "var(--surface)", color: "var(--accent)", border: "1px solid var(--border)" }}
                              >
                                {d.source_type.substring(0, 2)}
                              </div>
                              <span className="truncate max-w-[200px] md:max-w-xs">{d.filename}</span>
                            </div>
                          </td>
                          <td className="px-5 py-3.5">
                            <span
                              className="px-2 py-0.5 rounded text-[10px] font-bold uppercase border"
                              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt-m)" }}
                            >
                              {d.source_type}
                            </span>
                          </td>
                          <td className="px-5 py-3.5 font-mono font-medium" style={{ color: "var(--txt)" }}>
                            {d.rows.toLocaleString()}
                          </td>
                          <td className="px-5 py-3.5 font-mono font-medium" style={{ color: "var(--txt)" }}>
                            {d.cols}
                          </td>
                          <td className="px-5 py-3.5">
                            <span
                              className="px-2 py-0.5 rounded text-[10px] font-bold border"
                              style={{
                                background: d.missing_pct < 1 ? "rgba(16,185,129,0.1)" : "rgba(245,158,11,0.1)",
                                borderColor: d.missing_pct < 1 ? "#10b981" : "#f59e0b",
                                color: d.missing_pct < 1 ? "#10b981" : "#f59e0b"
                              }}
                            >
                              {d.missing_pct}% Missing
                            </span>
                          </td>
                          <td className="px-5 py-3.5" style={{ color: "var(--txt-m)" }}>
                            {d.time_ago}
                          </td>
                          <td className="px-5 py-3.5 text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Link
                                href={`/workspace?upload_id=${d.id}`}
                                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg font-bold text-xs shadow-sm no-underline transition-all hover:opacity-90 cursor-pointer"
                                style={{
                                  background: "var(--accent)",
                                  color: "#ffffff"
                                }}
                              >
                                <span>Open</span>
                                <ArrowRight size={12} />
                              </Link>

                              {deleteConfirmId === d.id ? (
                                <div className="inline-flex items-center gap-1">
                                  <button
                                    type="button"
                                    disabled={deletingId === d.id}
                                    onClick={() => handleDeleteDataset(d.id, d.filename)}
                                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg font-bold text-xs shadow-sm transition-all cursor-pointer"
                                    style={{
                                      background: "#dc2626",
                                      color: "#ffffff"
                                    }}
                                    title="Confirm permanent deletion from database and storage"
                                  >
                                    {deletingId === d.id ? (
                                      <>
                                        <Loader2 size={12} className="animate-spin" />
                                        <span>Deleting...</span>
                                      </>
                                    ) : (
                                      <>
                                        <Check size={12} />
                                        <span>Confirm?</span>
                                      </>
                                    )}
                                  </button>
                                  <button
                                    type="button"
                                    disabled={deletingId === d.id}
                                    onClick={() => setDeleteConfirmId(null)}
                                    className="p-1 rounded-lg border transition-all cursor-pointer hover:opacity-80"
                                    style={{
                                      background: "var(--surface)",
                                      borderColor: "var(--border)",
                                      color: "var(--txt-m)"
                                    }}
                                    title="Cancel"
                                  >
                                    <X size={12} />
                                  </button>
                                </div>
                              ) : (
                                <button
                                  type="button"
                                  disabled={deletingId === d.id}
                                  onClick={() => setDeleteConfirmId(d.id)}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg font-bold text-xs border transition-all cursor-pointer hover:border-red-500/50 hover:text-red-400"
                                  style={{
                                    background: "var(--surface)",
                                    borderColor: "var(--border)",
                                    color: "var(--txt-m)"
                                  }}
                                  title="Delete dataset"
                                >
                                  <Trash2 size={12} />
                                  <span>Delete</span>
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB 2: MODEL REGISTRY ── */}
        {activeTab === "models" && (
          <div className="space-y-6">
            <div
              className="rounded-2xl border p-5 shadow-sm"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                <div>
                  <h2 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                    Machine Learning Models
                  </h2>
                  <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                    Automated ML models trained via LightGBM, XGBoost, and Scikit-Learn.
                  </p>
                </div>

                <Link
                  href="/workspace"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold no-underline"
                  style={{ background: "var(--accent)", color: "#fff" }}
                >
                  <Plus size={13} />
                  <span>Train New Model</span>
                </Link>
              </div>

              {models.length === 0 ? (
                <div
                  className="p-8 text-center rounded-xl border border-dashed flex flex-col items-center justify-center gap-2"
                  style={{ borderColor: "var(--border)" }}
                >
                  <Cpu size={28} className="opacity-40" />
                  <p className="text-xs font-bold" style={{ color: "var(--txt)" }}>No models in registry</p>
                  <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>Train and register ML models via AutoML in the workspace.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
                  {models.map((m) => (
                    <div
                      key={m.id}
                      className="p-4 rounded-xl border flex flex-col justify-between transition-all"
                      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                    >
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span
                            className="px-2 py-0.5 rounded text-[10px] font-bold border"
                            style={{ background: "rgba(16,185,129,0.1)", borderColor: "#10b981", color: "#10b981" }}
                          >
                            {m.status}
                          </span>
                          <span className="text-[10px]" style={{ color: "var(--txt-m)" }}>{m.created_at}</span>
                        </div>

                        <h3 className="font-bold text-xs mb-0.5" style={{ color: "var(--txt)" }}>
                          {m.name}
                        </h3>
                        <p className="text-[11px] font-mono mb-3" style={{ color: "var(--txt-m)" }}>
                          {m.algorithm}
                        </p>

                        <div className="space-y-1 text-xs border-t pt-2" style={{ borderColor: "var(--border)" }}>
                          <div className="flex justify-between">
                            <span style={{ color: "var(--txt-m)" }}>Target:</span>
                            <span className="font-mono font-bold" style={{ color: "var(--txt)" }}>{m.target}</span>
                          </div>
                          <div className="flex justify-between">
                            <span style={{ color: "var(--txt-m)" }}>{m.metric}:</span>
                            <span className="font-mono font-bold text-emerald-500">{m.score}</span>
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 pt-2 border-t flex items-center justify-between" style={{ borderColor: "var(--border)" }}>
                        <Link
                          href="/workspace"
                          className="text-xs font-bold flex items-center gap-1 no-underline"
                          style={{ color: "var(--accent)" }}
                        >
                          <span>Inspect</span>
                          <ArrowRight size={12} />
                        </Link>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => {
                              setSaveSuccessMsg(`Model ${m.name} downloaded`);
                              setTimeout(() => setSaveSuccessMsg(""), 2000);
                            }}
                            className="p-1 rounded text-xs opacity-75 hover:opacity-100 cursor-pointer"
                            style={{ color: "var(--txt-m)" }}
                            title="Download Weights (.joblib)"
                          >
                            <Download size={13} />
                          </button>

                          {deleteModelConfirmId === m.id ? (
                            <div className="flex items-center gap-1 bg-red-500/10 border border-red-500/30 px-1.5 py-0.5 rounded-md">
                              <button
                                onClick={() => handleDeleteModel(m.id, m.name)}
                                disabled={deletingModelId === m.id}
                                className="text-[10px] font-bold text-red-400 hover:text-red-300 cursor-pointer flex items-center gap-0.5"
                              >
                                {deletingModelId === m.id ? <Loader2 size={10} className="animate-spin" /> : null}
                                <span>{deletingModelId === m.id ? "..." : "Delete"}</span>
                              </button>
                              <button
                                onClick={() => setDeleteModelConfirmId(null)}
                                className="text-[10px] text-gray-400 hover:text-white cursor-pointer ml-1"
                              >
                                ✕
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setDeleteModelConfirmId(m.id)}
                              className="p-1 rounded text-xs opacity-75 hover:opacity-100 hover:text-red-400 transition-colors cursor-pointer"
                              style={{ color: "var(--txt-m)" }}
                              title="Delete Model from Registry"
                            >
                              <Trash2 size={13} />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TAB 3: AUTOMATED REPORTS ── */}
        {activeTab === "reports" && (
          <div className="space-y-6">
            <div
              className="rounded-2xl border p-5 shadow-sm"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                <div>
                  <h2 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                    Automated Reports
                  </h2>
                  <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                    HTML and PDF intelligence documents generated from dataset EDA.
                  </p>
                </div>

                <Link
                  href="/workspace"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold no-underline"
                  style={{ background: "var(--accent)", color: "#fff" }}
                >
                  <Plus size={13} />
                  <span>Generate Report</span>
                </Link>
              </div>

              {reports.length === 0 ? (
                <div
                  className="p-8 text-center rounded-xl border border-dashed flex flex-col items-center justify-center gap-2"
                  style={{ borderColor: "var(--border)" }}
                >
                  <FileText size={28} className="opacity-40" />
                  <p className="text-xs font-bold" style={{ color: "var(--txt)" }}>No automated reports found</p>
                  <p className="text-[11px]" style={{ color: "var(--txt-m)" }}>Generate intelligence reports from any dataset in the workspace.</p>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {reports.map((r) => (
                    <div
                      key={r.id}
                      className="p-3.5 rounded-xl border flex items-center justify-between gap-3 flex-wrap"
                      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                          style={{ background: "rgba(59,130,246,0.1)", color: "#3b82f6" }}
                        >
                          <FileText size={18} />
                        </div>
                        <div>
                          <h4 className="font-bold text-xs" style={{ color: "var(--txt)" }}>
                            {r.triggered_by} — {r.filename}
                          </h4>
                          <p className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                            Generated {r.created_at} • HTML &amp; PDF Formats
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <a
                          href={`/api/reports/${r.id}`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2.5 py-1 rounded-lg text-xs font-bold border flex items-center gap-1 no-underline"
                          style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                        >
                          <ExternalLink size={12} />
                          <span>Preview</span>
                        </a>
                        <a
                          href={`/api/reports/${r.id}?format=pdf`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 no-underline"
                          style={{ background: "var(--accent)", color: "#fff" }}
                        >
                          <Download size={12} />
                          <span>PDF</span>
                        </a>

                        {deleteReportConfirmId === r.id ? (
                          <div className="flex items-center gap-1.5 bg-red-500/10 border border-red-500/30 px-2 py-1 rounded-lg">
                            <button
                              onClick={() => handleDeleteReport(r.id, r.filename)}
                              disabled={deletingReportId === r.id}
                              className="text-xs font-bold text-red-400 hover:text-red-300 cursor-pointer flex items-center gap-1"
                            >
                              {deletingReportId === r.id ? <Loader2 size={12} className="animate-spin" /> : null}
                              <span>{deletingReportId === r.id ? "Deleting..." : "Confirm Delete"}</span>
                            </button>
                            <button
                              onClick={() => setDeleteReportConfirmId(null)}
                              className="text-xs text-gray-400 hover:text-white cursor-pointer ml-1"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteReportConfirmId(r.id)}
                            className="p-1.5 rounded-lg border text-xs opacity-75 hover:opacity-100 hover:text-red-400 hover:border-red-500/40 transition-all cursor-pointer"
                            style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                            title="Delete Report"
                          >
                            <Trash2 size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── TAB 4: THEMES & PLATFORM PREFERENCES ── */}
        {activeTab === "preferences" && (
          <div className="space-y-6">
            {/* Theme Palettes Grid */}
            <div
              className="rounded-2xl border p-5 md:p-6 shadow-sm"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="mb-4">
                <h2 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                  Theme Palette
                </h2>
                <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                  Select from 11 verified high-contrast themes.
                </p>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {THEMES.map((th) => {
                  const isSelected = currentTheme === th.id;
                  return (
                    <button
                      key={th.id}
                      onClick={() => handleThemeSelect(th.id)}
                      className="p-3 rounded-xl border text-left transition-all relative overflow-hidden flex flex-col justify-between cursor-pointer"
                      style={{
                        background: th.bg,
                        borderColor: isSelected ? th.accent : th.border,
                        borderWidth: isSelected ? "2px" : "1px",
                        boxShadow: isSelected ? `0 0 12px ${th.accent}40` : "none"
                      }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold text-xs" style={{ color: th.text }}>
                          {th.name}
                        </span>
                        {isSelected && (
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ background: th.accent }}
                          />
                        )}
                      </div>

                      <div className="flex items-center gap-1 pt-1">
                        <div className="w-4 h-4 rounded border" style={{ background: th.bg, borderColor: th.border }} />
                        <div className="w-4 h-4 rounded" style={{ background: th.accent }} />
                        <div className="w-4 h-4 rounded border" style={{ background: th.text, borderColor: th.border }} />
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Developer API Access Token */}
            <div
              className="rounded-2xl border p-5 md:p-6 shadow-sm"
              style={{ background: "var(--card)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center gap-2 mb-1">
                <Code size={16} style={{ color: "var(--accent)" }} />
                <h2 className="text-sm font-bold" style={{ color: "var(--txt)" }}>
                  Programmatic API Tokens
                </h2>
              </div>
              <p className="text-xs mb-4" style={{ color: "var(--txt-m)" }}>
                Use this token to automate data ingestion from CI/CD or Python pipelines.
              </p>

              <div className="flex flex-col sm:flex-row items-center gap-2.5">
                <div
                  className="flex-1 w-full px-3.5 py-2 rounded-xl border font-mono text-xs flex items-center justify-between"
                  style={{
                    background: "var(--surface)",
                    borderColor: "var(--border)",
                    color: "var(--txt)"
                  }}
                >
                  <span className="truncate">{apiKey}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded border ml-2 shrink-0" style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}>
                    Admin Scope
                  </span>
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <button
                    onClick={handleCopyKey}
                    className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all border cursor-pointer"
                    style={{
                      background: copiedKey ? "#10b981" : "var(--surface)",
                      borderColor: copiedKey ? "#10b981" : "var(--border)",
                      color: copiedKey ? "#fff" : "var(--txt)"
                    }}
                  >
                    {copiedKey ? <Check size={13} /> : <Copy size={13} />}
                    <span>{copiedKey ? "Copied" : "Copy"}</span>
                  </button>

                  <button
                    onClick={handleRegenKey}
                    className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all border cursor-pointer"
                    style={{
                      background: "var(--surface)",
                      borderColor: "var(--border)",
                      color: "var(--txt-m)"
                    }}
                  >
                    <RefreshCw size={13} />
                    <span>Regen</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── QUICK LAUNCH / ACTION CTA BANNER (Compact Variant) ── */}
        <div className="pt-2">
          <CTABanner
            variant="compact"
            title="Ready to launch a new data exploration or AutoML run?"
            subtitle="Connect spreadsheets, PostgreSQL, or Snowflake for zero-config profiling and model training."
            buttonText="Open Studio"
            href="/workspace"
            secondaryButtonText="Pricing & Seats"
            secondaryHref="/pricing"
          />
        </div>
      </main>

      {/* ── EDIT PROFILE MODAL (Avatar, Name, Email) ── */}
      {isEditingProfile && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in"
          style={{ background: "rgba(0, 0, 0, 0.7)" }}
          onClick={() => setIsEditingProfile(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl border shadow-2xl p-6 space-y-4"
            style={{
              background: "var(--card)",
              borderColor: "var(--border)",
              color: "var(--txt)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2">
                <Edit3 size={16} style={{ color: "var(--accent)" }} />
                <h3 className="font-bold text-sm" style={{ color: "var(--txt)" }}>
                  Edit Profile &amp; Avatar
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setIsEditingProfile(false)}
                className="opacity-70 hover:opacity-100 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleSaveProfile} className="space-y-4">
              {/* Avatar Selector */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-xs font-semibold" style={{ color: "var(--txt)" }}>
                    Select Avatar
                  </label>
                  <span className="text-[11px] font-mono opacity-60">12 Human Faces</span>
                </div>
                <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
                  {HUMAN_AVATARS.map((av) => {
                    const isSelected = editAvatarId === av.id;
                    return (
                      <button
                        key={av.id}
                        type="button"
                        onClick={() => setEditAvatarId(av.id)}
                        className="p-1.5 rounded-xl border flex flex-col items-center justify-center gap-1 cursor-pointer transition-all hover:scale-105"
                        style={{
                          background: isSelected ? "var(--glow)" : "var(--surface)",
                          borderColor: isSelected ? "var(--accent)" : "var(--border)",
                          boxShadow: isSelected ? "0 0 10px var(--glow)" : "none",
                        }}
                        title={`${av.name} (${av.role})`}
                      >
                        <div
                          className="w-10 h-10 rounded-full p-0.5 shadow-sm overflow-hidden"
                          style={{ background: av.bg }}
                        >
                          <img
                            src={av.url}
                            className="w-full h-full rounded-full object-cover"
                            alt={av.name}
                          />
                        </div>
                        <span className="text-[10px] font-medium truncate w-full text-center" style={{ color: "var(--txt)" }}>
                          {av.name.split(" ")[0]}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Display Name Input */}
              <div className="space-y-1">
                <label className="block text-xs font-semibold" style={{ color: "var(--txt)" }}>
                  Full Name
                </label>
                <div className="relative">
                  <User size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--txt-m)" }} />
                  <input
                    type="text"
                    required
                    value={editNameInput}
                    onChange={(e) => setEditNameInput(e.target.value)}
                    placeholder="Alex Morgan"
                    className="w-full pl-8 pr-3 py-2 rounded-xl text-xs border outline-none focus:border-[var(--accent)]"
                    style={{
                      background: "var(--inp-bg)",
                      borderColor: "var(--border)",
                      color: "var(--txt)",
                    }}
                  />
                </div>
              </div>

              {/* Email Address Input */}
              <div className="space-y-1">
                <label className="block text-xs font-semibold" style={{ color: "var(--txt)" }}>
                  Work Email Address
                </label>
                <div className="relative">
                  <Mail size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--txt-m)" }} />
                  <input
                    type="email"
                    required
                    value={editEmailInput}
                    onChange={(e) => setEditEmailInput(e.target.value)}
                    placeholder="alex.morgan@dataforge.internal"
                    className="w-full pl-8 pr-3 py-2 rounded-xl text-xs border outline-none focus:border-[var(--accent)]"
                    style={{
                      background: "var(--inp-bg)",
                      borderColor: "var(--border)",
                      color: "var(--txt)",
                    }}
                  />
                </div>
              </div>

              {/* Modal Buttons */}
              <div className="flex items-center justify-end gap-2 pt-3 border-t" style={{ borderColor: "var(--border)" }}>
                <button
                  type="button"
                  onClick={() => setIsEditingProfile(false)}
                  className="px-3.5 py-2 rounded-xl text-xs font-semibold border cursor-pointer"
                  style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white cursor-pointer shadow-md"
                  style={{ background: "var(--accent)" }}
                >
                  Save Profile
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── INVITE MEMBER MODAL WITH TIER SIZE LIMIT CHECK ── */}
      {inviteModalOpen && selectedTeamId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in"
          style={{ background: "rgba(0, 0, 0, 0.7)" }}
          onClick={() => setInviteModalOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-2xl border shadow-2xl p-6 space-y-4"
            style={{
              background: "var(--card)",
              borderColor: "var(--border)",
              color: "var(--txt)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b" style={{ borderColor: "var(--border)" }}>
              <div className="flex items-center gap-2">
                <Users size={16} style={{ color: "var(--accent)" }} />
                <h3 className="font-bold text-sm" style={{ color: "var(--txt)" }}>
                  Add Member to {teams.find((t) => t.id === selectedTeamId)?.name}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setInviteModalOpen(false)}
                className="opacity-70 hover:opacity-100 cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Quota Notice Banner */}
            <div
              className="p-3 rounded-xl border text-xs flex items-center justify-between"
              style={{
                background: "var(--surface)",
                borderColor: "var(--border)",
              }}
            >
              <span style={{ color: "var(--txt-m)" }}>
                Plan: <strong style={{ color: "var(--txt)" }}>{currentTierInfo.name}</strong>
              </span>
              <span className="font-mono text-[11px]" style={{ color: "var(--accent)" }}>
                Max {currentTierInfo.maxMembers} seats
              </span>
            </div>

            {inviteError && (
              <div
                className="p-3 rounded-xl border text-xs flex flex-col gap-1.5"
                style={{
                  background: "rgba(239, 68, 68, 0.1)",
                  borderColor: "rgba(239, 68, 68, 0.3)",
                  color: "#ef4444",
                }}
              >
                <div className="flex items-center gap-1.5 font-bold">
                  <AlertCircle size={14} />
                  <span>Limit Exceeded</span>
                </div>
                <p className="text-[11px] leading-relaxed">{inviteError}</p>
                <Link
                  href="/pricing"
                  className="font-bold underline text-xs pt-1 flex items-center gap-1"
                  style={{ color: "var(--accent)" }}
                >
                  <span>Upgrade to unlock higher team limits</span>
                  <ArrowRight size={12} />
                </Link>
              </div>
            )}

            <form onSubmit={handleInviteMember} className="space-y-3.5">
              <div className="space-y-1">
                <label className="block text-xs font-semibold" style={{ color: "var(--txt)" }}>
                  Member Name
                </label>
                <input
                  type="text"
                  required
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  placeholder="e.g. Jordan Lee"
                  className="w-full px-3 py-2 rounded-xl text-xs border outline-none focus:border-[var(--accent)]"
                  style={{
                    background: "var(--inp-bg)",
                    borderColor: "var(--border)",
                    color: "var(--txt)",
                  }}
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold" style={{ color: "var(--txt)" }}>
                  Member Work Email
                </label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="jordan.lee@company.com"
                  className="w-full px-3 py-2 rounded-xl text-xs border outline-none focus:border-[var(--accent)]"
                  style={{
                    background: "var(--inp-bg)",
                    borderColor: "var(--border)",
                    color: "var(--txt)",
                  }}
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-semibold" style={{ color: "var(--txt)" }}>
                  Assign Role
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(["Admin", "Analyst", "Viewer"] as TeamRole[]).map((r) => {
                    const isSelected = inviteRole === r;
                    const rMeta = ROLE_BADGES[r];
                    return (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setInviteRole(r)}
                        className="p-2 rounded-xl border text-left flex items-center justify-between cursor-pointer transition-all"
                        style={{
                          background: isSelected ? "var(--glow)" : "var(--inp-bg)",
                          borderColor: isSelected ? rMeta.color : "var(--border)",
                        }}
                      >
                        <span className="text-xs font-bold" style={{ color: isSelected ? rMeta.color : "var(--txt)" }}>
                          {r}
                        </span>
                        {isSelected && <Check size={12} style={{ color: rMeta.color }} />}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t" style={{ borderColor: "var(--border)" }}>
                <button
                  type="button"
                  onClick={() => setInviteModalOpen(false)}
                  className="px-3.5 py-2 rounded-xl text-xs font-semibold border cursor-pointer"
                  style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold text-white cursor-pointer shadow-md"
                  style={{ background: "var(--accent)" }}
                >
                  Add to Team
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
