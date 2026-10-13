"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ThemeSwitcher from "../components/ThemeSwitcher";
import UserMenu from "../components/UserMenu";
import Logo from "../components/Logo";
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
} from "lucide-react";

interface DatasetItem {
  id: number;
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

export type TeamRole = "Admin" | "Data Engineer" | "Analyst" | "Viewer";

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: TeamRole;
  avatarEmoji?: string;
  avatarBg?: string;
}

export interface TeamItem {
  id: string;
  name: string;
  myRole: TeamRole;
  members: TeamMember[];
}

export interface AvatarOption {
  id: string;
  emoji: string;
  label: string;
  bg: string;
}

const AVATAR_OPTIONS: AvatarOption[] = [
  { id: "avatar-1", emoji: "⚡", label: "Cyber Spark", bg: "linear-gradient(135deg, #3b82f6, #06b6d4)" },
  { id: "avatar-2", emoji: "🔮", label: "Quantum Violet", bg: "linear-gradient(135deg, #8b5cf6, #ec4899)" },
  { id: "avatar-3", emoji: "🌿", label: "Emerald Matrix", bg: "linear-gradient(135deg, #10b981, #059669)" },
  { id: "avatar-4", emoji: "🪐", label: "Solar Amber", bg: "linear-gradient(135deg, #f59e0b, #ef4444)" },
  { id: "avatar-5", emoji: "💎", label: "Diamond Ice", bg: "linear-gradient(135deg, #06b6d4, #3b82f6)" },
  { id: "avatar-6", emoji: "🦊", label: "Crimson Ember", bg: "linear-gradient(135deg, #ef4444, #f97316)" },
  { id: "avatar-7", emoji: "🚀", label: "Apollo Indigo", bg: "linear-gradient(135deg, #6366f1, #3b82f6)" },
  { id: "avatar-8", emoji: "👑", label: "Royal Gold", bg: "linear-gradient(135deg, #eab308, #ca8a04)" },
];

const ROLE_BADGES: Record<TeamRole, { label: string; color: string; glow: string }> = {
  Admin: { label: "Admin", color: "#8b5cf6", glow: "rgba(139,92,246,0.15)" },
  "Data Engineer": { label: "Data Engineer", color: "#10b981", glow: "rgba(16,185,129,0.15)" },
  Analyst: { label: "Analyst", color: "#3b82f6", glow: "rgba(59,130,246,0.15)" },
  Viewer: { label: "Viewer", color: "#f59e0b", glow: "rgba(245,158,11,0.15)" },
};

const TIER_LIMITS: Record<string, { name: string; maxMembers: number; badgeColor: string }> = {
  free: { name: "Free Starter", maxMembers: 1, badgeColor: "#64748b" },
  pro: { name: "Pro Analyst", maxMembers: 5, badgeColor: "#3b82f6" },
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

  // Teams State
  const [teams, setTeams] = useState<TeamItem[]>([
    {
      id: "team-1",
      name: "Core Analytics Studio",
      myRole: "Admin",
      members: [
        { id: "m-1", name: "Alex Morgan", email: "alex.morgan@dataforge.internal", role: "Admin", avatarEmoji: "⚡", avatarBg: "linear-gradient(135deg, #3b82f6, #06b6d4)" },
        { id: "m-2", name: "Sarah Chen", email: "sarah.chen@dataforge.internal", role: "Data Engineer", avatarEmoji: "🌿", avatarBg: "linear-gradient(135deg, #10b981, #059669)" },
        { id: "m-3", name: "Marcus Vance", email: "marcus.v@dataforge.internal", role: "Analyst", avatarEmoji: "🔮", avatarBg: "linear-gradient(135deg, #8b5cf6, #ec4899)" },
      ],
    },
    {
      id: "team-2",
      name: "Production Data Platform",
      myRole: "Data Engineer",
      members: [
        { id: "m-4", name: "David Kim", email: "david.kim@dataforge.internal", role: "Admin", avatarEmoji: "👑", avatarBg: "linear-gradient(135deg, #eab308, #ca8a04)" },
        { id: "m-5", name: "Alex Morgan", email: "alex.morgan@dataforge.internal", role: "Data Engineer", avatarEmoji: "⚡", avatarBg: "linear-gradient(135deg, #3b82f6, #06b6d4)" },
        { id: "m-6", name: "Elena Rostova", email: "elena.r@dataforge.internal", role: "Data Engineer", avatarEmoji: "💎", avatarBg: "linear-gradient(135deg, #06b6d4, #3b82f6)" },
      ],
    },
    {
      id: "team-3",
      name: "Growth & Revenue Quants",
      myRole: "Analyst",
      members: [
        { id: "m-7", name: "Maya Patel", email: "maya.patel@dataforge.internal", role: "Admin", avatarEmoji: "🦊", avatarBg: "linear-gradient(135deg, #ef4444, #f97316)" },
        { id: "m-8", name: "Alex Morgan", email: "alex.morgan@dataforge.internal", role: "Analyst", avatarEmoji: "⚡", avatarBg: "linear-gradient(135deg, #3b82f6, #06b6d4)" },
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

  // Reports
  const [reports, setReports] = useState<any[]>([
    { id: 101, filename: "customer_churn_q3.csv", triggered_by: "Executive Briefing", created_at: "Today, 08:30 AM" },
    { id: 102, filename: "sales_pipeline_2026.csv", triggered_by: "Weekly Automated EDA", created_at: "Yesterday" }
  ]);

  // API Token State
  const [apiKey, setApiKey] = useState<string>("df_live_948f2a893cb4e921d78");
  const [copiedKey, setCopiedKey] = useState<boolean>(false);

  // Theme & Preferences
  const [currentTheme, setCurrentTheme] = useState<string>("dark");

  // Load Initial Data from Backend & LocalStorage
  useEffect(() => {
    // 1. Restore role, avatar & theme
    const savedRole = localStorage.getItem("df_user_role") as TeamRole | null;
    if (savedRole && (savedRole === "Admin" || savedRole === "Data Engineer" || savedRole === "Analyst" || savedRole === "Viewer")) {
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

    // 2. Check cached user
    try {
      const rawUser = localStorage.getItem("df_user_cache");
      if (rawUser) {
        const u = JSON.parse(rawUser);
        if (u.name) setUserName(u.name);
        if (u.email) setUserEmail(u.email);
        if (u.avatar) setUserAvatarId(u.avatar);
      }
    } catch (e) {}

    // 3. Check cached teams
    try {
      const rawTeams = localStorage.getItem("df_teams_data");
      if (rawTeams) {
        const parsed = JSON.parse(rawTeams);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setTeams(parsed);
        }
      }
    } catch (e) {}

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

    const randomAvatar = AVATAR_OPTIONS[Math.floor(Math.random() * AVATAR_OPTIONS.length)];
    const newMember: TeamMember = {
      id: `m-${Date.now()}`,
      name: inviteName.trim(),
      email: inviteEmail.trim(),
      role: inviteRole,
      avatarEmoji: randomAvatar.emoji,
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

    setInviteModalOpen(false);
    setSaveSuccessMsg(`Added ${newMember.name} as ${newMember.role}`);
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

  const currentAvatar = AVATAR_OPTIONS.find((a) => a.id === userAvatarId) || AVATAR_OPTIONS[0];
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
                className="w-14 h-14 md:w-16 md:h-16 rounded-2xl flex items-center justify-center text-2xl shadow-md shrink-0 border relative group cursor-pointer"
                onClick={handleOpenEditProfile}
                style={{
                  background: currentAvatar.bg,
                  borderColor: "var(--border)",
                  boxShadow: `0 0 20px ${currentRoleMeta.glow}`,
                }}
                title="Click to edit avatar"
              >
                <span>{currentAvatar.emoji}</span>
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
                            <div className="flex items-center gap-1.5 truncate">
                              <span
                                className="w-4 h-4 rounded-full flex items-center justify-center text-[9px] shrink-0"
                                style={{ background: m.avatarBg || "var(--accent)" }}
                              >
                                {m.avatarEmoji || "👤"}
                              </span>
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
              {datasets.length || stats.uploads}
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
                    {datasets.map((d) => (
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
                          <Link
                            href={`/workspace?upload_id=${d.id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg font-bold text-xs shadow-sm no-underline transition-all"
                            style={{
                              background: "var(--accent)",
                              color: "#ffffff"
                            }}
                          >
                            <span>Open</span>
                            <ArrowRight size={12} />
                          </Link>
                        </td>
                      </tr>
                    ))}
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
                    </div>
                  </div>
                ))}
              </div>
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
                    </div>
                  </div>
                ))}
              </div>
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
                <label className="block text-xs font-semibold mb-2" style={{ color: "var(--txt)" }}>
                  Select Avatar
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {AVATAR_OPTIONS.map((av) => {
                    const isSelected = editAvatarId === av.id;
                    return (
                      <button
                        key={av.id}
                        type="button"
                        onClick={() => setEditAvatarId(av.id)}
                        className="p-2.5 rounded-xl border flex flex-col items-center justify-center gap-1 cursor-pointer transition-all"
                        style={{
                          background: isSelected ? "var(--glow)" : "var(--surface)",
                          borderColor: isSelected ? "var(--accent)" : "var(--border)",
                          boxShadow: isSelected ? "0 0 10px var(--glow)" : "none",
                        }}
                      >
                        <span
                          className="w-8 h-8 rounded-full flex items-center justify-center text-sm shadow-sm"
                          style={{ background: av.bg }}
                        >
                          {av.emoji}
                        </span>
                        <span className="text-[10px] font-medium truncate w-full text-center" style={{ color: "var(--txt)" }}>
                          {av.label}
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
                <div className="grid grid-cols-2 gap-2">
                  {(["Admin", "Data Engineer", "Analyst", "Viewer"] as TeamRole[]).map((r) => {
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
