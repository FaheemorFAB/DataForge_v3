"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
  RefreshCw,
  Link2,
  Check,
  Globe,
  Lock,
  Shield,
  Trash2,
  UserPlus,
  X,
  Copy,
  ChevronDown,
  Loader2,
  Sparkles,
  Info,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export type ShareRole = "Viewer" | "Analyst" | "Admin";

interface Collaborator {
  email: string;
  role: ShareRole;
  name?: string;
  avatar?: string;
  invited_at?: string;
  user_id?: number;
}

interface ShareData {
  upload_id: string;
  owner_id?: number;
  owner_email?: string;
  owner_name?: string;
  owner_avatar?: string;
  general_access: "restricted" | "anyone_with_link";
  link_role: ShareRole;
  share_token?: string;
  collaborators: Collaborator[];
}

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  uploadId: string;
  datasetName?: string;
  onRoleChanged?: (newRole: string) => void;
}

export default function ShareModal({
  isOpen,
  onClose,
  uploadId,
  datasetName = "Dataset",
  onRoleChanged,
}: ShareModalProps) {
  const { user } = useAuth();
  const [shareData, setShareData] = useState<ShareData | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<string>("Viewer");
  const [isOwner, setIsOwner] = useState(false);
  const [userTier, setUserTier] = useState<string>("free");
  const [hasTeamCollaboration, setHasTeamCollaboration] = useState<boolean>(false);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Invite input state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<ShareRole>("Viewer");
  const [isInviting, setIsInviting] = useState(false);

  // Link copy state
  const [copied, setCopied] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);

  useEffect(() => {
    if (isOpen && uploadId) {
      loadShareData();
    }
  }, [isOpen, uploadId]);

  const loadShareData = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const urlParams = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
      const token = urlParams?.get("share_token") || "";
      const res = await apiFetch(`/workspace/${uploadId}/share${token ? `?share_token=${token}` : ""}`);
      if (res.ok) {
        const json = await res.json();
        setShareData(json.shares);
        setCurrentUserRole(json.current_user_role || "Viewer");
        setIsOwner(json.is_owner || false);
        setUserTier(json.user_tier || "free");
        setHasTeamCollaboration(Boolean(json.has_team_collaboration));
        if (onRoleChanged && json.current_user_role) {
          onRoleChanged(json.current_user_role);
        }
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Failed to load sharing settings");
      }
    } catch {
      setErrorMsg("Network error connecting to share service");
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim() || !inviteEmail.includes("@")) {
      setErrorMsg("Please enter a valid email address.");
      return;
    }
    setIsInviting(true);
    setErrorMsg("");
    setSuccessMsg("");
    try {
      const res = await apiFetch(`/workspace/${uploadId}/share/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      });
      if (res.ok) {
        const json = await res.json();
        setShareData(json.shares);
        setInviteEmail("");
        const delivery = json.shares?.last_delivery;
        if (delivery?.sent) {
          setSuccessMsg(`✓ Invitation email dispatched to ${inviteEmail} as ${inviteRole}!`);
        } else {
          setSuccessMsg(`✓ Added ${inviteEmail} (${inviteRole}). Relay simulated (add SMTP/Resend keys in .env); link is ready below.`);
        }
        setTimeout(() => setSuccessMsg(""), 5000);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Failed to invite collaborator");
      }
    } catch {
      setErrorMsg("Failed to invite collaborator");
    } finally {
      setIsInviting(false);
    }
  };

  const handleUpdateRole = async (email: string, newRole: ShareRole) => {
    setErrorMsg("");
    try {
      const res = await apiFetch(`/workspace/${uploadId}/share/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, role: newRole }),
      });
      if (res.ok) {
        const json = await res.json();
        setShareData(json.shares);
      }
    } catch {
      setErrorMsg("Failed to update collaborator role");
    }
  };

  const handleRemoveCollaborator = async (email: string) => {
    setErrorMsg("");
    try {
      const res = await apiFetch(`/workspace/${uploadId}/share/collaborators`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (res.ok) {
        const json = await res.json();
        setShareData(json.shares);
      }
    } catch {
      setErrorMsg("Failed to remove collaborator");
    }
  };

  const handleUpdateGeneralAccess = async (access: "restricted" | "anyone_with_link", role: ShareRole) => {
    setErrorMsg("");
    try {
      const res = await apiFetch(`/workspace/${uploadId}/share/general`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ general_access: access, link_role: role }),
      });
      if (res.ok) {
        const json = await res.json();
        setShareData(json.shares);
      }
    } catch {
      setErrorMsg("Failed to update general link settings");
    }
  };

  const handleRegenerateToken = async () => {
    if (!window.confirm("Regenerating the share token will immediately invalidate any previous links sent to colleagues. Do you want to proceed?")) {
      return;
    }
    setIsRegenerating(true);
    setErrorMsg("");
    try {
      const res = await apiFetch(`/workspace/${uploadId}/share/regenerate`, {
        method: "POST",
      });
      if (res.ok) {
        const json = await res.json();
        setShareData(json.shares);
        setSuccessMsg("✓ New share link generated! Previous links are now revoked.");
        setTimeout(() => setSuccessMsg(""), 4000);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Failed to regenerate share token");
      }
    } catch {
      setErrorMsg("Failed to regenerate share token");
    } finally {
      setIsRegenerating(false);
    }
  };

  const handleCopyLink = () => {
    if (typeof window === "undefined") return;
    const shareUrl = `${window.location.origin}/workspace?upload_id=${uploadId}${
      shareData?.general_access === "anyone_with_link" && shareData.share_token
        ? `&share_token=${shareData.share_token}`
        : ""
    }`;
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (!isOpen) return null;

  // Tier gating: role assignment & member invites require Team Collaboration plan
  const effectiveTeamCollaboration = hasTeamCollaboration || userTier === "team" || userTier === "enterprise";

  // Authentic owner email: filter out internal fallback dummies like user_3@dataforge.app
  const displayedOwnerEmail =
    shareData?.owner_email && !shareData.owner_email.startsWith("user_") && shareData.owner_email.includes("@")
      ? shareData.owner_email
      : (isOwner && user?.email ? user.email : (shareData?.owner_email || "owner@dataforge.internal"));

  return (
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center p-3 sm:p-5 backdrop-blur-md animate-fadeIn"
      style={{ background: "rgba(0, 0, 0, 0.65)" }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden flex flex-col relative animate-slideUp"
        style={{
          background: "var(--card, var(--surface, #ffffff))",
          border: "1px solid var(--border)",
          color: "var(--txt)",
          boxShadow: "0 25px 60px -15px rgba(0,0,0,0.4), 0 0 30px var(--glow)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header (Google Sheets Style) */}
        <div
          className="px-6 py-4 border-b flex items-center justify-between"
          style={{ borderColor: "var(--border)", background: "var(--nav)" }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center border"
              style={{
                background: "var(--glow)",
                borderColor: "var(--accent)",
                color: "var(--accent)",
              }}
            >
              <Users size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold tracking-tight" style={{ color: "var(--txt)" }}>
                Share
              </h2>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center border hover:opacity-80 transition-opacity"
            style={{ borderColor: "var(--border)", color: "var(--txt-m)", background: "var(--surface)" }}
            aria-label="Close Share Dialog"
          >
            <X size={15} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center gap-3">
              <Loader2 size={24} className="animate-spin" style={{ color: "var(--accent)" }} />
              <span className="text-xs font-semibold" style={{ color: "var(--txt-m)" }}>
                Loading share permissions...
              </span>
            </div>
          ) : (
            <>
          {/* Notifications */}
          {errorMsg && (
            <div
              className="p-3 rounded-xl text-xs font-semibold flex items-center gap-2"
              style={{ background: "rgba(239, 68, 68, 0.1)", color: "#EF4444", border: "1px solid rgba(239, 68, 68, 0.2)" }}
            >
              <Info size={14} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div
              className="p-3 rounded-xl text-xs font-semibold flex items-center gap-2"
              style={{ background: "rgba(16, 185, 129, 0.1)", color: "#10B981", border: "1px solid rgba(16, 185, 129, 0.2)" }}
            >
              <Check size={14} className="shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Section 1: Add People & Groups by Email (Team Collaboration Only) */}
          {effectiveTeamCollaboration && (
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider mb-2" style={{ color: "var(--txt-m)" }}>
                Add people and groups
              </label>
              <form onSubmit={handleInvite} className="flex flex-col sm:flex-row gap-2">
                <div
                  className="flex-1 flex items-center gap-2 px-3.5 py-2 rounded-xl border"
                  style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                >
                  <UserPlus size={15} style={{ color: "var(--txt-m)" }} />
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="Enter colleague email address..."
                    className="w-full bg-transparent text-xs font-medium outline-none"
                    style={{ color: "var(--txt)" }}
                    disabled={!isOwner && currentUserRole !== "Admin"}
                  />
                </div>

                <div className="flex gap-2">
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as ShareRole)}
                    className="px-3 py-2 rounded-xl border text-xs font-bold outline-none cursor-pointer"
                    style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--txt)" }}
                    disabled={!isOwner && currentUserRole !== "Admin"}
                  >
                    <option value="Viewer">Viewer</option>
                    <option value="Analyst">Analyst</option>
                    <option value="Admin">Admin</option>
                  </select>

                  <button
                    type="submit"
                    disabled={isInviting || (!isOwner && currentUserRole !== "Admin") || !inviteEmail.trim()}
                    className="px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all disabled:opacity-50 cursor-pointer shadow-sm"
                    style={{ background: "var(--accent)", color: "#ffffff" }}
                  >
                    {isInviting ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                    <span>Invite</span>
                  </button>
                </div>
              </form>
              {!isOwner && currentUserRole !== "Admin" && (
                <p className="text-[11px] mt-1.5" style={{ color: "var(--txt-m)" }}>
                  * Only dataset Owners and Admins can invite new collaborators.
                </p>
              )}
            </div>
          )}

          {/* Section 2: People with Access */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider mb-2.5" style={{ color: "var(--txt-m)" }}>
              People with access
            </label>
            <div className="space-y-2">
              {/* Owner */}
              <div
                className="flex items-center justify-between p-3 rounded-xl border transition-all"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="relative w-9 h-9 rounded-full overflow-hidden border shrink-0 flex items-center justify-center font-bold text-xs"
                    style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}
                  >
                    {shareData?.owner_avatar ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img
                        src={shareData.owner_avatar}
                        alt={shareData?.owner_name || "Owner"}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.currentTarget as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : null}
                    <span>
                      {(shareData?.owner_name || displayedOwnerEmail || "O")[0].toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <div className="text-xs font-bold flex items-center gap-1.5" style={{ color: "var(--txt)" }}>
                      <span>{shareData?.owner_name || "Dataset Owner"}</span>
                      {isOwner && (
                        <span className="text-[10px] font-semibold px-1.5 py-0.2 rounded" style={{ background: "var(--glow)", color: "var(--accent)" }}>
                          (You)
                        </span>
                      )}
                    </div>
                    <div className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                      {displayedOwnerEmail} • Owner (Full access)
                    </div>
                  </div>
                </div>
                <span
                  className="px-2.5 py-1 rounded-full text-[10px] font-bold border shrink-0"
                  style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}
                >
                  Owner
                </span>
              </div>

              {/* Invited Collaborators or Solo Plan Information */}
              {effectiveTeamCollaboration ? (
                shareData?.collaborators && shareData.collaborators.length > 0 ? (
                  shareData.collaborators.map((c) => (
                    <div
                      key={c.email}
                      className="flex items-center justify-between p-3 rounded-xl border transition-all"
                      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                    >
                      <div className="flex items-center gap-3 truncate mr-2">
                        <div
                          className="relative w-8 h-8 rounded-full overflow-hidden border shrink-0 flex items-center justify-center font-bold text-xs"
                          style={{ borderColor: "var(--border)", background: "var(--card)", color: "var(--txt)" }}
                        >
                          {c.avatar ? (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img
                              src={c.avatar}
                              alt={c.name || c.email}
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                (e.currentTarget as HTMLElement).style.display = "none";
                              }}
                            />
                          ) : null}
                          <span>
                            {(c.name || c.email)[0].toUpperCase()}
                          </span>
                        </div>
                        <div className="truncate">
                          <div className="text-xs font-bold truncate" style={{ color: "var(--txt)" }}>
                            {c.name || c.email.split("@")[0]}
                          </div>
                          <div className="text-[10px] truncate" style={{ color: "var(--txt-m)" }}>
                            {c.email} • {c.role === "Viewer" ? "Read-only: view data, charts & reports" : c.role === "Analyst" ? "Can query, clean, chart & train AutoML" : "Full access: invite, export & administer"}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        {isOwner || currentUserRole === "Admin" ? (
                          <>
                            <select
                              value={c.role}
                              onChange={(e) => handleUpdateRole(c.email, e.target.value as ShareRole)}
                              className="px-2.5 py-1 rounded-lg border text-xs font-semibold outline-none cursor-pointer"
                              style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                            >
                              <option value="Viewer">Viewer</option>
                              <option value="Analyst">Analyst</option>
                              <option value="Admin">Admin</option>
                            </select>
                            <button
                              onClick={() => handleRemoveCollaborator(c.email)}
                              className="p-1.5 rounded-lg border hover:text-red-500 hover:border-red-500 transition-colors cursor-pointer"
                              style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                              title="Remove collaborator"
                            >
                              <Trash2 size={13} />
                            </button>
                          </>
                        ) : (
                          <span
                            className="px-2.5 py-1 rounded-full text-[10px] font-bold border"
                            style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                          >
                            {c.role}
                          </span>
                        )}
                      </div>
                    </div>
                  ))
                ) : (
                  <div
                    className="p-4 rounded-xl border border-dashed text-center text-xs"
                    style={{ borderColor: "var(--border)", color: "var(--txt-m)" }}
                  >
                    No colleagues invited yet. Add someone above to collaborate.
                  </div>
                )
              ) : (
                <div
                  className="p-3 rounded-xl border flex items-center justify-between text-xs"
                  style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
                >
                  <div className="flex items-center gap-2">
                    <Shield size={13} style={{ color: "var(--accent)" }} />
                    <span>Solo Workspace • Role collaboration (Admin, Analyst, Viewer) is exclusive to Team Collaboration.</span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0" style={{ borderColor: "var(--border)", color: "var(--txt)" }}>
                    {userTier === "pro" ? "Pro Analyst" : "Free Starter"}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Section 3: General Access (Google Sheets Style) */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider mb-2.5" style={{ color: "var(--txt-m)" }}>
              General access
            </label>
            <div
              className="p-4 rounded-xl border flex flex-col gap-3.5"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 border mt-0.5"
                  style={{
                    background:
                      shareData?.general_access === "anyone_with_link"
                        ? "rgba(16, 185, 129, 0.12)"
                        : "rgba(0, 0, 0, 0.05)",
                    borderColor:
                      shareData?.general_access === "anyone_with_link"
                        ? "#10B981"
                        : "var(--border)",
                    color:
                      shareData?.general_access === "anyone_with_link"
                        ? "#10B981"
                        : "var(--txt-m)",
                  }}
                >
                  {shareData?.general_access === "anyone_with_link" ? <Globe size={18} /> : <Lock size={18} />}
                </div>

                <div className="flex-1 min-w-0">
                  {/* Selectors Row */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      {(isOwner || currentUserRole === "Admin") ? (
                        <select
                          value={shareData?.general_access || "restricted"}
                          onChange={(e) =>
                            handleUpdateGeneralAccess(
                              e.target.value as "restricted" | "anyone_with_link",
                              shareData?.link_role || "Viewer"
                            )
                          }
                          className="px-2.5 py-1.5 rounded-lg border text-xs font-bold outline-none cursor-pointer"
                          style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                        >
                          <option value="restricted">Restricted</option>
                          <option value="anyone_with_link">Anyone with the link</option>
                        </select>
                      ) : (
                        <span className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                          {shareData?.general_access === "anyone_with_link" ? "Anyone with the link" : "Restricted"}
                        </span>
                      )}

                      {shareData?.general_access === "anyone_with_link" && (
                        (isOwner || currentUserRole === "Admin") && effectiveTeamCollaboration ? (
                          <select
                            value={shareData?.link_role || "Viewer"}
                            onChange={(e) =>
                              handleUpdateGeneralAccess("anyone_with_link", e.target.value as ShareRole)
                            }
                            className="px-2.5 py-1.5 rounded-lg border text-xs font-semibold outline-none cursor-pointer"
                            style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                          >
                            <option value="Viewer">Viewer (Read-only)</option>
                            <option value="Analyst">Analyst (Can analyze & chart)</option>
                          </select>
                        ) : (
                          <span
                            className="px-2.5 py-1.5 rounded-lg border text-xs font-semibold"
                            style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt-m)" }}
                          >
                            Viewer
                          </span>
                        )
                      )}
                    </div>
                  </div>

                  {/* Dynamic description */}
                  <p className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
                    {shareData?.general_access === "anyone_with_link"
                      ? effectiveTeamCollaboration
                        ? "Anyone on the internet with this secret link can open and inspect this dataset."
                        : "Anyone on the internet with this link can view this dataset in read-only mode."
                      : effectiveTeamCollaboration
                      ? "Only people explicitly added above by email can access with this link."
                      : "Only you (the owner) can access this dataset."}
                  </p>
                </div>
              </div>

              {/* Live Link URL Preview & Action Box */}
              <div
                className="p-2 sm:p-2.5 rounded-xl border flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2 text-xs"
                style={{ background: "var(--card)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center gap-2 truncate text-[11px] font-mono px-1 flex-1 min-w-0" style={{ color: "var(--txt-m)" }}>
                  <Link2 size={13} className="shrink-0" style={{ color: "var(--accent)" }} />
                  <span className="truncate">
                    {typeof window !== "undefined"
                      ? `${window.location.origin}/workspace?upload_id=${uploadId}${
                          shareData?.general_access === "anyone_with_link" && shareData.share_token
                            ? `&share_token=${shareData.share_token}`
                            : ""
                        }`
                      : "Link ready..."}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
                  <button
                    type="button"
                    onClick={handleCopyLink}
                    className="px-2.5 py-1 rounded-lg border text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer hover:border-[var(--accent)]"
                    style={{
                      background: copied ? "rgba(16, 185, 129, 0.15)" : "var(--surface)",
                      borderColor: copied ? "#10B981" : "var(--border)",
                      color: copied ? "#10B981" : "var(--txt)",
                    }}
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />}
                    <span>{copied ? "Copied" : "Copy"}</span>
                  </button>

                  {isOwner && shareData?.general_access === "anyone_with_link" && (
                    <button
                      type="button"
                      onClick={handleRegenerateToken}
                      disabled={isRegenerating}
                      className="px-2.5 py-1 rounded-lg border text-[11px] font-semibold flex items-center gap-1 transition-all cursor-pointer text-red-400 hover:text-red-300 hover:border-red-500/40 hover:bg-red-500/10 disabled:opacity-50"
                      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
                      title="Invalidate old link and issue a new secret token"
                    >
                      <RefreshCw size={11} className={isRegenerating ? "animate-spin" : ""} />
                      <span>{isRegenerating ? "Resetting..." : "Reset link"}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
            </>
          )}
        </div>

        {/* Footer (Copy link & Done) */}
        <div
          className="px-6 py-4 border-t flex items-center justify-between"
          style={{ borderColor: "var(--border)", background: "var(--nav)" }}
        >
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold border transition-all hover:border-[var(--accent)] hover:text-[var(--accent)] cursor-pointer"
            style={{
              background: "var(--surface)",
              borderColor: copied ? "#10B981" : "var(--border)",
              color: copied ? "#10B981" : "var(--txt)",
            }}
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span>{copied ? "Link copied!" : "Copy link"}</span>
          </button>

          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl text-xs font-bold transition-all hover:opacity-90 cursor-pointer shadow-sm"
            style={{ background: "var(--accent)", color: "#ffffff" }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
