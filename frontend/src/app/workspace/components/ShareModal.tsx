"use client";

import React, { useState, useEffect } from "react";
import {
  Users,
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

export type ShareRole = "Viewer" | "Analyst" | "Editor" | "Admin";

interface Collaborator {
  email: string;
  role: ShareRole;
  invited_at?: string;
  user_id?: number;
}

interface ShareData {
  upload_id: string;
  owner_id?: number;
  owner_email?: string;
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
  const [shareData, setShareData] = useState<ShareData | null>(null);
  const [currentUserRole, setCurrentUserRole] = useState<string>("Viewer");
  const [isOwner, setIsOwner] = useState(false);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Invite input state
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<ShareRole>("Viewer");
  const [isInviting, setIsInviting] = useState(false);

  // Link copy state
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen && uploadId) {
      loadShareData();
    }
  }, [isOpen, uploadId]);

  const loadShareData = async () => {
    setLoading(true);
    setErrorMsg("");
    try {
      const res = await apiFetch(`/workspace/${uploadId}/share`);
      if (res.ok) {
        const json = await res.json();
        setShareData(json.shares);
        setCurrentUserRole(json.current_user_role || "Viewer");
        setIsOwner(json.is_owner || false);
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
              <h2 className="text-base font-bold truncate max-w-xs sm:max-w-md" style={{ color: "var(--txt)" }}>
                Share &ldquo;{datasetName}&rdquo;
              </h2>
              <div className="flex items-center gap-2 text-[11px]" style={{ color: "var(--txt-m)" }}>
                <span>User-level access control</span>
                <span>•</span>
                <span className="font-semibold" style={{ color: "var(--accent)" }}>
                  Your role: {currentUserRole}
                </span>
              </div>
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

          {/* Section 1: Add People & Groups by Email */}
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
                  <option value="Editor">Editor</option>
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

          {/* Section 2: People with Access */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider mb-2.5" style={{ color: "var(--txt-m)" }}>
              People with access
            </label>
            <div className="space-y-2">
              {/* Owner */}
              <div
                className="flex items-center justify-between p-3 rounded-xl border"
                style={{ background: "var(--surface)", borderColor: "var(--border)" }}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                    style={{ background: "var(--glow)", color: "var(--accent)", border: "1px solid var(--accent)" }}
                  >
                    {(shareData?.owner_email || "U")[0].toUpperCase()}
                  </div>
                  <div>
                    <div className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                      {shareData?.owner_email || "Dataset Owner"}
                    </div>
                    <div className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                      Owner • Full permissions
                    </div>
                  </div>
                </div>
                <span
                  className="px-2.5 py-1 rounded-full text-[10px] font-bold border"
                  style={{ background: "var(--glow)", borderColor: "var(--accent)", color: "var(--accent)" }}
                >
                  Owner
                </span>
              </div>

              {/* Invited Collaborators */}
              {shareData?.collaborators && shareData.collaborators.length > 0 ? (
                shareData.collaborators.map((c) => (
                  <div
                    key={c.email}
                    className="flex items-center justify-between p-3 rounded-xl border"
                    style={{ background: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <div className="flex items-center gap-3 truncate mr-2">
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                        style={{ background: "rgba(0,0,0,0.06)", color: "var(--txt)" }}
                      >
                        {c.email[0].toUpperCase()}
                      </div>
                      <div className="truncate">
                        <div className="text-xs font-bold truncate" style={{ color: "var(--txt)" }}>
                          {c.email}
                        </div>
                        <div className="text-[10px]" style={{ color: "var(--txt-m)" }}>
                          {c.role === "Viewer" && "Read-only access"}
                          {c.role === "Analyst" && "Can query, analyze, and chart"}
                          {c.role === "Editor" && "Can edit, clean, and join tables"}
                          {c.role === "Admin" && "Can invite, manage and export"}
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
                            <option value="Editor">Editor</option>
                            <option value="Admin">Admin</option>
                          </select>
                          <button
                            onClick={() => handleRemoveCollaborator(c.email)}
                            className="p-1.5 rounded-lg border hover:text-red-500 hover:border-red-500 transition-colors"
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
              )}
            </div>
          </div>

          {/* Section 3: General Access (Google Sheets Style) */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider mb-2.5" style={{ color: "var(--txt-m)" }}>
              General access
            </label>
            <div
              className="p-4 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3"
              style={{ background: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="flex items-start gap-3">
                <div
                  className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border mt-0.5"
                  style={{
                    background:
                      shareData?.general_access === "anyone_with_link"
                        ? "rgba(16, 185, 129, 0.1)"
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
                <div>
                  <div className="text-xs font-bold" style={{ color: "var(--txt)" }}>
                    {shareData?.general_access === "anyone_with_link" ? "Anyone with the link" : "Restricted"}
                  </div>
                  <div className="text-[11px] leading-relaxed" style={{ color: "var(--txt-m)" }}>
                    {shareData?.general_access === "anyone_with_link"
                      ? "Anyone on the internet with this link can view or analyze this dataset."
                      : "Only people with explicit email access can open with the link."}
                  </div>
                </div>
              </div>

              {/* General Access Dropdowns */}
              <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                {(isOwner || currentUserRole === "Admin") && (
                  <>
                    <select
                      value={shareData?.general_access || "restricted"}
                      onChange={(e) =>
                        handleUpdateGeneralAccess(
                          e.target.value as "restricted" | "anyone_with_link",
                          shareData?.link_role || "Viewer"
                        )
                      }
                      className="px-2.5 py-1.5 rounded-lg border text-xs font-semibold outline-none cursor-pointer"
                      style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                    >
                      <option value="restricted">Restricted</option>
                      <option value="anyone_with_link">Anyone with link</option>
                    </select>

                    {shareData?.general_access === "anyone_with_link" && (
                      <select
                        value={shareData?.link_role || "Viewer"}
                        onChange={(e) =>
                          handleUpdateGeneralAccess("anyone_with_link", e.target.value as ShareRole)
                        }
                        className="px-2.5 py-1.5 rounded-lg border text-xs font-semibold outline-none cursor-pointer"
                        style={{ background: "var(--card)", borderColor: "var(--border)", color: "var(--txt)" }}
                      >
                        <option value="Viewer">Viewer</option>
                        <option value="Analyst">Analyst</option>
                        <option value="Editor">Editor</option>
                      </select>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
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
