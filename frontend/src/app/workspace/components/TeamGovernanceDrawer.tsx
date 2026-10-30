"use client";

import React, { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import {
  Users,
  Shield,
  Activity,
  UserPlus,
  Trash2,
  CheckCircle2,
  X,
  ChevronDown,
  Building,
  Plus,
  Lock,
  Sparkles,
  RefreshCw,
  Search,
  Check,
  Loader2,
  AlertCircle,
} from "lucide-react";

interface TeamMember {
  id: string;
  org_id: string;
  user_id: number;
  user_email: string;
  user_name: string;
  role: "Admin" | "Analyst" | "Viewer";
  joined_at: string;
  capabilities?: string[];
}

interface Organization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  owner_id: number;
  created_at: string;
  my_role?: string;
  member_count?: number;
}

interface AuditLog {
  id: string;
  org_id: string;
  user_id: number;
  user_email: string;
  action: string;
  target: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

interface TeamGovernanceDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentOrgId?: string;
  onOrgChange?: (org: Organization) => void;
}

export function TeamGovernanceDrawer({
  isOpen,
  onClose,
  currentOrgId,
  onOrgChange,
}: TeamGovernanceDrawerProps) {
  const [activeTab, setActiveTab] = useState<"members" | "matrix" | "audit">("members");
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeOrg, setActiveOrg] = useState<Organization | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [capabilitiesMatrix, setCapabilitiesMatrix] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(false);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [createOrgModalOpen, setCreateOrgModalOpen] = useState(false);

  // Revoke member confirm state (inline confirmation instead of window alert)
  const [revokeConfirmId, setRevokeConfirmId] = useState<number | null>(null);
  const [revokingId, setRevokingId] = useState<number | null>(null);

  // Invite form state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<"Admin" | "Analyst" | "Viewer">("Analyst");
  const [inviteError, setInviteError] = useState("");
  const [inviteSubmitting, setInviteSubmitting] = useState(false);

  // Create team form state
  const [newTeamName, setNewTeamName] = useState("");
  const [newTeamPlan, setNewTeamPlan] = useState("Enterprise");
  const [createTeamError, setCreateTeamError] = useState("");
  const [createSubmitting, setCreateSubmitting] = useState(false);

  // Search & filter
  const [searchQuery, setSearchQuery] = useState("");
  const [auditSearch, setAuditSearch] = useState("");

  const fetchOrganizations = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiFetch("/teams");
      if (res.ok) {
        const data = await res.json();
        const orgs: Organization[] = data.organizations || [];
        setOrganizations(orgs);
        if (orgs.length > 0) {
          const selected = currentOrgId
            ? orgs.find((o) => o.id === currentOrgId) || orgs[0]
            : orgs[0];
          setActiveOrg(selected);
          if (onOrgChange) onOrgChange(selected);
        }
      }
    } catch (e) {
      console.error("Failed to load organizations:", e);
    } finally {
      setLoading(false);
    }
  }, [currentOrgId, onOrgChange]);

  const fetchOrgDetails = useCallback(async (orgId: string) => {
    try {
      const [membersRes, auditRes, capRes] = await Promise.all([
        apiFetch(`/teams/${orgId}/members`),
        apiFetch(`/teams/${orgId}/audit-logs?limit=100`),
        apiFetch(`/teams/roles/capabilities`),
      ]);

      if (membersRes.ok) {
        const mData = await membersRes.json();
        setMembers(mData.members || []);
      }
      if (auditRes.ok) {
        const aData = await auditRes.json();
        setAuditLogs(aData.logs || []);
      }
      if (capRes.ok) {
        const cData = await capRes.json();
        setCapabilitiesMatrix(cData.capabilities || {});
      }
    } catch (e) {
      console.error("Failed to load team details:", e);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchOrganizations();
    }
  }, [isOpen, fetchOrganizations]);

  useEffect(() => {
    if (activeOrg) {
      fetchOrgDetails(activeOrg.id);
    }
  }, [activeOrg, fetchOrgDetails]);

  const handleOrgSwitch = (org: Organization) => {
    setActiveOrg(org);
    if (onOrgChange) onOrgChange(org);
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOrg) return;
    if (!inviteEmail.trim() || !inviteEmail.includes("@")) {
      setInviteError("Please enter a valid work email address.");
      return;
    }
    setInviteSubmitting(true);
    setInviteError("");

    try {
      const res = await apiFetch(`/teams/${activeOrg.id}/invite`, {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail.trim(),
          name: inviteName.trim() || undefined,
          role: inviteRole,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        setInviteError(err.detail || "Failed to invite member");
      } else {
        setInviteModalOpen(false);
        setInviteEmail("");
        setInviteName("");
        fetchOrgDetails(activeOrg.id);
      }
    } catch (err: any) {
      setInviteError(err.message || "Network error");
    } finally {
      setInviteSubmitting(false);
    }
  };

  const handleRoleChange = async (targetUserId: number, newRole: string) => {
    if (!activeOrg) return;
    try {
      const res = await apiFetch(`/teams/${activeOrg.id}/members/${targetUserId}/role`, {
        method: "PATCH",
        body: JSON.stringify({ new_role: newRole }),
      });
      if (res.ok) {
        fetchOrgDetails(activeOrg.id);
      }
    } catch (e) {
      console.error("Failed to update role:", e);
    }
  };

  const handleRemoveMember = async (targetUserId: number) => {
    if (!activeOrg) return;
    setRevokingId(targetUserId);

    try {
      const res = await apiFetch(`/teams/${activeOrg.id}/members/${targetUserId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        fetchOrgDetails(activeOrg.id);
      }
    } catch (e) {
      console.error("Failed to remove member:", e);
    } finally {
      setRevokingId(null);
      setRevokeConfirmId(null);
    }
  };

  const handleCreateTeam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTeamName.trim()) {
      setCreateTeamError("Please enter a team / organization name.");
      return;
    }
    setCreateTeamError("");
    setCreateSubmitting(true);

    try {
      const res = await apiFetch("/teams", {
        method: "POST",
        body: JSON.stringify({
          name: newTeamName.trim(),
          plan: newTeamPlan,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setCreateOrgModalOpen(false);
        setNewTeamName("");
        await fetchOrganizations();
        if (data.organization) {
          setActiveOrg(data.organization);
          if (onOrgChange) onOrgChange(data.organization);
        }
      }
    } catch (e) {
      console.error("Failed to create team:", e);
    } finally {
      setCreateSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const roleColor = (role: string) => {
    switch (role) {
      case "Admin":
        return { bg: "rgba(239, 68, 68, 0.12)", border: "rgba(239, 68, 68, 0.35)", text: "#ef4444" };
      case "Analyst":
        return { bg: "rgba(6, 182, 212, 0.12)", border: "rgba(6, 182, 212, 0.35)", text: "#06b6d4" };
      default:
        return { bg: "rgba(148, 163, 184, 0.12)", border: "rgba(148, 163, 184, 0.35)", text: "#94a3b8" };
    }
  };

  const filteredMembers = members.filter(
    (m) =>
      m.user_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.user_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.role.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredAuditLogs = auditLogs.filter(
    (a) =>
      a.action.toLowerCase().includes(auditSearch.toLowerCase()) ||
      a.target.toLowerCase().includes(auditSearch.toLowerCase()) ||
      a.user_email.toLowerCase().includes(auditSearch.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity duration-200">
      <div
        className="relative w-full max-w-2xl h-full shadow-2xl flex flex-col border-l transition-transform duration-300"
        style={{
          background: "var(--bg)",
          borderColor: "var(--border)",
          color: "var(--txt)",
        }}
      >
        {/* HEADER */}
        <div
          className="flex items-center justify-between p-4 border-b shrink-0"
          style={{ background: "var(--nav)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
              style={{
                background: "rgba(255, 67, 16, 0.12)",
                color: "var(--accent)",
                border: "1px solid rgba(255, 67, 16, 0.3)",
              }}
            >
              <Building size={20} />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold truncate">
                  {activeOrg?.name || "Team Workspace"}
                </h2>
                <span
                  className="px-2 py-0.5 text-[10px] font-black uppercase rounded-full tracking-wider"
                  style={{
                    background: "rgba(16, 185, 129, 0.15)",
                    color: "#10b981",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                  }}
                >
                  {activeOrg?.plan || "Enterprise"}
                </span>
              </div>
              <p className="text-xs truncate" style={{ color: "var(--txt-m)" }}>
                Multi-Tenant Governance & Role-Based Access Control
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* ORG SWITCHER DROPDOWN */}
            <div className="relative group">
              <button
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold border transition-colors cursor-pointer"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                  color: "var(--txt)",
                }}
                title="Switch Team Workspace"
              >
                <span>Switch Team</span>
                <ChevronDown size={13} />
              </button>

              <div
                className="absolute right-0 top-full mt-1 w-56 rounded-xl border p-1 shadow-xl hidden group-hover:block group-focus-within:block z-50"
                style={{
                  background: "var(--card)",
                  borderColor: "var(--border)",
                }}
              >
                <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider" style={{ color: "var(--txt-f)" }}>
                  Your Workspaces
                </div>
                {organizations.map((org) => (
                  <button
                    key={org.id}
                    onClick={() => handleOrgSwitch(org)}
                    className="w-full flex items-center justify-between px-2.5 py-1.5 text-xs rounded-lg text-left transition-colors cursor-pointer hover:bg-black/5 dark:hover:bg-white/5"
                    style={{
                      fontWeight: activeOrg?.id === org.id ? "700" : "500",
                      color: activeOrg?.id === org.id ? "var(--accent)" : "var(--txt)",
                    }}
                  >
                    <span className="truncate">{org.name}</span>
                    {activeOrg?.id === org.id && <CheckCircle2 size={13} />}
                  </button>
                ))}
                <div className="my-1 border-t" style={{ borderColor: "var(--border)" }} />
                <button
                  onClick={() => setCreateOrgModalOpen(true)}
                  className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs font-bold rounded-lg text-left transition-colors cursor-pointer"
                  style={{ color: "var(--accent)" }}
                >
                  <Plus size={13} />
                  <span>Create New Team</span>
                </button>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
              style={{ color: "var(--txt-m)" }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* TABS SUB-NAV */}
        <div
          className="flex items-center gap-1 px-4 border-b shrink-0 text-xs font-bold"
          style={{ background: "var(--nav)", borderColor: "var(--border)" }}
        >
          <button
            onClick={() => setActiveTab("members")}
            className={`flex items-center gap-1.5 py-3 px-3 border-b-2 transition-colors cursor-pointer ${
              activeTab === "members" ? "border-[var(--accent)]" : "border-transparent"
            }`}
            style={{ color: activeTab === "members" ? "var(--txt)" : "var(--txt-m)" }}
          >
            <Users size={14} />
            <span>Team Members ({members.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("matrix")}
            className={`flex items-center gap-1.5 py-3 px-3 border-b-2 transition-colors cursor-pointer ${
              activeTab === "matrix" ? "border-[var(--accent)]" : "border-transparent"
            }`}
            style={{ color: activeTab === "matrix" ? "var(--txt)" : "var(--txt-m)" }}
          >
            <Shield size={14} />
            <span>Role Capabilities</span>
          </button>
          <button
            onClick={() => setActiveTab("audit")}
            className={`flex items-center gap-1.5 py-3 px-3 border-b-2 transition-colors cursor-pointer ${
              activeTab === "audit" ? "border-[var(--accent)]" : "border-transparent"
            }`}
            style={{ color: activeTab === "audit" ? "var(--txt)" : "var(--txt-m)" }}
          >
            <Activity size={14} />
            <span>Governance Audit Trail ({auditLogs.length})</span>
          </button>
        </div>

        {/* TAB BODY */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === "members" && (
            <div className="space-y-4">
              {/* TOOLBAR */}
              <div className="flex items-center justify-between gap-3">
                <div
                  className="flex items-center gap-2 px-3 py-1.5 rounded-xl border flex-1 text-xs"
                  style={{ background: "var(--card)", borderColor: "var(--border)" }}
                >
                  <Search size={14} style={{ color: "var(--txt-m)" }} />
                  <input
                    type="text"
                    placeholder="Search by name, email or role..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-transparent border-none outline-none w-full text-xs"
                    style={{ color: "var(--txt)" }}
                  />
                </div>

                <button
                  onClick={() => setInviteModalOpen(true)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all hover:scale-[1.02] cursor-pointer"
                  style={{
                    background: "var(--accent)",
                    color: "white",
                  }}
                >
                  <UserPlus size={14} />
                  <span>Invite Member</span>
                </button>
              </div>

              {/* MEMBERS LIST */}
              <div
                className="rounded-xl border divide-y overflow-hidden"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                {filteredMembers.map((m) => {
                  const badge = roleColor(m.role);
                  return (
                    <div
                      key={m.id}
                      className="p-3.5 flex items-center justify-between gap-4 transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className="w-9 h-9 rounded-full flex items-center justify-center font-black text-xs shrink-0"
                          style={{
                            background: badge.bg,
                            color: badge.text,
                            border: `1px solid ${badge.border}`,
                          }}
                        >
                          {m.user_name.slice(0, 2).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-xs truncate">{m.user_name}</span>
                            <span
                              className="px-2 py-0.5 rounded-md text-[10px] font-bold"
                              style={{
                                background: badge.bg,
                                color: badge.text,
                                border: `1px solid ${badge.border}`,
                              }}
                            >
                              {m.role}
                            </span>
                          </div>
                          <div className="text-[11px] truncate" style={{ color: "var(--txt-m)" }}>
                            {m.user_email}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {/* ROLE SELECTOR */}
                        <select
                          value={m.role}
                          onChange={(e) => handleRoleChange(m.user_id, e.target.value)}
                          className="px-2 py-1 text-xs rounded-lg border bg-transparent font-medium cursor-pointer"
                          style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                        >
                          <option value="Admin">Admin</option>
                          <option value="Analyst">Analyst</option>
                          <option value="Viewer">Viewer</option>
                        </select>

                        {revokeConfirmId === m.user_id ? (
                          <div className="inline-flex items-center gap-1">
                            <button
                              type="button"
                              disabled={revokingId === m.user_id}
                              onClick={() => handleRemoveMember(m.user_id)}
                              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg font-bold text-xs shadow-sm transition-all cursor-pointer"
                              style={{
                                background: "#dc2626",
                                color: "#ffffff",
                              }}
                              title="Confirm revoke access"
                            >
                              {revokingId === m.user_id ? (
                                <>
                                  <Loader2 size={12} className="animate-spin" />
                                  <span>Revoking...</span>
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
                              disabled={revokingId === m.user_id}
                              onClick={() => setRevokeConfirmId(null)}
                              className="p-1 rounded-lg border transition-all cursor-pointer hover:opacity-80"
                              style={{
                                background: "var(--surface)",
                                borderColor: "var(--border)",
                                color: "var(--txt-m)",
                              }}
                              title="Cancel"
                            >
                              <X size={12} />
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            disabled={revokingId === m.user_id}
                            onClick={() => setRevokeConfirmId(m.user_id)}
                            className="p-1.5 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors cursor-pointer"
                            title="Revoke Member Access"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeTab === "matrix" && (
            <div className="space-y-4">
              <p className="text-xs" style={{ color: "var(--txt-m)" }}>
                Role-Based Access Control matrix defines capabilities enforced across ingestion,
                joins, cleaning, model training, and production serving.
              </p>

              <div
                className="rounded-xl border overflow-hidden"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div
                  className="grid grid-cols-3 p-3 font-bold text-xs border-b"
                  style={{ background: "var(--nav)", borderColor: "var(--border)" }}
                >
                  <div style={{ color: "#ef4444" }}>Admin (Level 3)</div>
                  <div style={{ color: "#06b6d4" }}>Analyst (Level 2)</div>
                  <div style={{ color: "#94a3b8" }}>Viewer (Level 1)</div>
                </div>

                <div className="grid grid-cols-3 p-3 text-xs gap-3">
                  {["Admin", "Analyst", "Viewer"].map((roleName) => (
                    <div key={roleName} className="space-y-2">
                      {(capabilitiesMatrix[roleName] || []).map((cap, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-1.5 text-[11px] leading-tight"
                        >
                          <CheckCircle2
                            size={12}
                            className="shrink-0 mt-0.5"
                            style={{ color: roleColor(roleName).text }}
                          />
                          <span>{cap}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "audit" && (
            <div className="space-y-4">
              <div
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <Search size={14} style={{ color: "var(--txt-m)" }} />
                <input
                  type="text"
                  placeholder="Filter audit events by action, target or user..."
                  value={auditSearch}
                  onChange={(e) => setAuditSearch(e.target.value)}
                  className="bg-transparent border-none outline-none w-full text-xs"
                  style={{ color: "var(--txt)" }}
                />
              </div>

              <div
                className="rounded-xl border divide-y overflow-hidden"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                {filteredAuditLogs.length === 0 ? (
                  <div className="p-8 text-center text-xs" style={{ color: "var(--txt-m)" }}>
                    No audit logs recorded matching this filter.
                  </div>
                ) : (
                  filteredAuditLogs.map((log) => (
                    <div key={log.id} className="p-3 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider font-mono"
                            style={{
                              background: "rgba(255, 67, 16, 0.12)",
                              color: "var(--accent)",
                            }}
                          >
                            {log.action}
                          </span>
                          <span className="font-bold">{log.target}</span>
                        </div>
                        <span className="text-[10px] font-mono" style={{ color: "var(--txt-f)" }}>
                          {new Date(log.timestamp).toLocaleTimeString()} ·{" "}
                          {new Date(log.timestamp).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]" style={{ color: "var(--txt-m)" }}>
                        <span>Initiated by: {log.user_email}</span>
                        {log.metadata && Object.keys(log.metadata).length > 0 && (
                          <span className="font-mono text-[10px] opacity-80">
                            {JSON.stringify(log.metadata)}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* INVITE MODAL */}
        {inviteModalOpen && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div
              className="w-full max-w-md rounded-2xl border p-5 shadow-2xl space-y-4"
              style={{ background: "var(--bg)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <UserPlus size={18} style={{ color: "var(--accent)" }} />
                  <h3 className="font-bold text-sm">Invite Team Collaborator</h3>
                </div>
                <button
                  onClick={() => setInviteModalOpen(false)}
                  className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10"
                >
                  <X size={16} />
                </button>
              </div>

              {inviteError && (
                <div className="p-2.5 rounded-xl text-xs bg-red-500/10 text-red-500 border border-red-500/20">
                  {inviteError}
                </div>
              )}

              <form noValidate onSubmit={handleInvite} className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Corporate Email Address
                  </label>
                  <input
                    type="email"
                    placeholder="colleague@company.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl text-xs border bg-transparent outline-none focus:border-[var(--accent)]"
                    style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Full Name (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="Sarah Chen"
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl text-xs border bg-transparent outline-none focus:border-[var(--accent)]"
                    style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Assigned Role
                  </label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-xl text-xs border bg-transparent outline-none cursor-pointer"
                    style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                  >
                    <option value="Admin">Admin (Full Control, Team Management & Production Deploy)</option>
                    <option value="Analyst">Analyst (EDA, AutoML, Dashboards, SQL Analytics)</option>
                    <option value="Viewer">Viewer (Read-Only Dashboards & Summaries)</option>
                  </select>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setInviteModalOpen(false)}
                    className="px-3 py-2 rounded-xl text-xs font-semibold border transition-colors cursor-pointer"
                    style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={inviteSubmitting}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-white transition-all cursor-pointer"
                    style={{ background: "var(--accent)" }}
                  >
                    {inviteSubmitting ? "Inviting..." : "Send Invitation"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* CREATE TEAM MODAL */}
        {createOrgModalOpen && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div
              className="w-full max-w-md rounded-2xl border p-5 shadow-2xl space-y-4"
              style={{ background: "var(--bg)", borderColor: "var(--border)" }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Building size={18} style={{ color: "var(--accent)" }} />
                  <h3 className="font-bold text-sm">Create New Team Workspace</h3>
                </div>
                <button
                  onClick={() => setCreateOrgModalOpen(false)}
                  className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10"
                >
                  <X size={16} />
                </button>
              </div>

              {createTeamError && (
                <div className="p-2.5 rounded-xl text-xs bg-red-500/10 border border-red-500/30 text-red-500 flex items-center gap-1.5 font-medium mb-3">
                  <AlertCircle size={13} />
                  <span>{createTeamError}</span>
                </div>
              )}

              <form noValidate onSubmit={handleCreateTeam} className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Team / Organization Name
                  </label>
                  <input
                    type="text"
                    placeholder="BioTech Quant Labs"
                    value={newTeamName}
                    onChange={(e) => { setNewTeamName(e.target.value); if (createTeamError) setCreateTeamError(""); }}
                    className="w-full px-3 py-2 rounded-xl text-xs border bg-transparent outline-none focus:border-[var(--accent)]"
                    style={{ borderColor: "var(--border)", color: "var(--txt)" }}
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold mb-1" style={{ color: "var(--txt-m)" }}>
                    Workspace Scope &amp; Environment
                  </label>
                  <select
                    value={newTeamPlan}
                    onChange={(e) => setNewTeamPlan(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl text-xs border outline-none cursor-pointer"
                    style={{ borderColor: "var(--border)", color: "var(--txt)", background: "var(--inp-bg)" }}
                  >
                    <option value="Enterprise">Shared Team Workspace (Multi-User Collaboration)</option>
                    <option value="Production">Production Analytics Environment</option>
                    <option value="Staging">Sandbox / Staging Research Cluster</option>
                  </select>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setCreateOrgModalOpen(false)}
                    className="px-3 py-2 rounded-xl text-xs font-semibold border transition-colors cursor-pointer"
                    style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createSubmitting}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-white transition-all cursor-pointer"
                    style={{ background: "var(--accent)" }}
                  >
                    {createSubmitting ? "Creating..." : "Create Organization"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
