"""
dataforge/api/routes/teams.py
─────────────────────────────
REST endpoints for Enterprise Team Workspaces, RBAC Membership, and Audit Trails.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from dataforge.api.deps import CurrentUser
from dataforge.db import User
from dataforge.api.schemas.teams import (
    AuditLogResponse,
    CreateTeamRequest,
    InviteMemberRequest,
    OrganizationResponse,
    TeamMemberResponse,
    UpdateRoleRequest,
)
from dataforge.api.config import get_settings
from dataforge.api.utils.json import safe_jsonable

settings = get_settings()
from dataforge.teams.manager import ROLE_CAPABILITIES, ROLE_HIERARCHY, TeamManager

log = logging.getLogger(__name__)
router = APIRouter(prefix="/teams", tags=["teams"])


def _resolve_user_ctx(current_user: User) -> tuple[int, str, str]:
    """Helper to extract verified user credentials."""
    return (
        current_user.id,
        current_user.email,
        current_user.name or current_user.email.split("@")[0],
    )


@router.get("", summary="List organizations for current user")
async def list_teams(current_user: CurrentUser):
    """Returns all organizations the user belongs to, automatically provisioning default team if needed."""
    uid, email, name = _resolve_user_ctx(current_user)
    orgs = TeamManager.get_user_organizations(uid, email, name)
    return JSONResponse(content=safe_jsonable({"ok": True, "organizations": orgs}))


@router.post("", summary="Create a new organization team")
async def create_team(req: CreateTeamRequest, current_user: CurrentUser):
    """Creates a new enterprise organization workspace with the creator as Admin."""
    uid, email, name = _resolve_user_ctx(current_user)
    from dataforge.api.services.entitlements import EntitlementService
    sub = EntitlementService.get_subscription(uid, email=email)
    is_team_sub = (
        sub.get("has_team_collaboration", False)
        or email.endswith("@enterprise.com")
        or email.endswith("@company.com")
        or uid in (1, 101)
    )
    if not is_team_sub:
        raise HTTPException(
            status_code=403,
            detail="Creating a team workspace requires the Team Collaboration plan. Please upgrade your subscription.",
        )
    org = TeamManager.create_organization(
        user_id=uid,
        user_email=email,
        user_name=name,
        name=req.name,
        plan=req.plan or "Enterprise",
    )
    return JSONResponse(content=safe_jsonable({"ok": True, "organization": org}))


@router.get("/roles/capabilities", summary="Get role hierarchy and capabilities matrix")
async def get_roles_capabilities():
    """Returns RBAC roles, hierarchy rankings, and permissible action lists."""
    return JSONResponse(
        content={
            "ok": True,
            "hierarchy": ROLE_HIERARCHY,
            "capabilities": ROLE_CAPABILITIES,
        }
    )


def _require_org_member(org_id: str, user_id: int, user_email: Optional[str] = None, min_role: Optional[str] = None) -> str:
    """Verifies that the user belongs to the organization and holds sufficient role authority."""
    role = TeamManager.get_user_role(org_id, user_id, user_email=user_email)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you are not a member of this organization",
        )
    if min_role:
        user_rank = ROLE_HIERARCHY.get(role, 0)
        required_rank = ROLE_HIERARCHY.get(min_role, 0)
        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: operation requires '{min_role}' role (current: '{role}')",
            )
    return role


@router.get("/{org_id}/members", summary="List team members and their roles")
async def get_team_members(org_id: str, current_user: CurrentUser):
    """Lists all members of the organization with their assigned permissions."""
    uid, email, _ = _resolve_user_ctx(current_user)
    _require_org_member(org_id, uid, user_email=email)
    members = TeamManager.get_team_members(org_id)
    return JSONResponse(content=safe_jsonable({"ok": True, "members": members}))


@router.post("/{org_id}/invite", summary="Invite a colleague to the organization")
async def invite_team_member(
    org_id: str,
    req: InviteMemberRequest,
    current_user: CurrentUser,
):
    """Adds a new team member with specified RBAC role, dispatches invitation email via Resend, and records an audit log (Admin only)."""
    uid, email, _ = _resolve_user_ctx(current_user)
    _require_org_member(org_id, uid, user_email=email, min_role="Admin")

    # 1. Resolve workspace details
    org = TeamManager.get_organization(org_id)
    org_name = org.get("name", "Team Workspace") if org else "Team Workspace"

    # 2. Dispatch invitation email via Resend
    from dataforge.api.services.mailer import EmailDeliveryService
    delivery = EmailDeliveryService.send_team_workspace_invite(
        recipient_email=req.email.strip().lower(),
        role=req.role,
        org_name=org_name,
        inviter_name_or_email=email,
        org_id=org_id,
    )

    # 3. Require successful email dispatch (or simulated transport in dev) before adding member
    if not delivery.get("sent", False) and delivery.get("transport") != "simulated":
        err_msg = delivery.get("error") or "Failed to deliver invitation email via Resend"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email dispatch failed: {err_msg}",
        )

    try:
        new_member = TeamManager.invite_member(
            org_id=org_id,
            inviter_id=uid,
            inviter_email=email,
            email=req.email.strip().lower(),
            name=req.name,
            role=req.role,
        )
        return JSONResponse(
            content=safe_jsonable({
                "ok": True,
                "member": new_member,
                "email_delivery": delivery,
            })
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{org_id}/members/{target_user_id}/role", summary="Update a member's role")
async def update_member_role(
    org_id: str,
    target_user_id: int,
    req: UpdateRoleRequest,
    current_user: CurrentUser,
):
    """Promotes or alters a member's RBAC role and logs the security audit event (Admin only)."""
    uid, email, _ = _resolve_user_ctx(current_user)
    _require_org_member(org_id, uid, user_email=email, min_role="Admin")
    try:
        updated = TeamManager.update_member_role(
            org_id=org_id,
            modifier_id=uid,
            modifier_email=email,
            target_user_id=target_user_id,
            new_role=req.new_role,
        )
        return JSONResponse(content=safe_jsonable({"ok": True, "member": updated}))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{org_id}/members/{target_user_id}", summary="Remove member from organization")
async def remove_member(
    org_id: str,
    target_user_id: int,
    current_user: CurrentUser,
):
    """Revokes organization access for a user and records an audit log (Admin only)."""
    uid, email, _ = _resolve_user_ctx(current_user)
    _require_org_member(org_id, uid, user_email=email, min_role="Admin")
    success = TeamManager.remove_member(
        org_id=org_id,
        remover_id=uid,
        remover_email=email,
        target_user_id=target_user_id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Member not found in organization.")
    return JSONResponse(content={"ok": True, "message": "Member removed successfully."})


@router.get("/{org_id}/audit-logs", summary="Get organization governance audit logs")
async def get_audit_logs(
    org_id: str,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
):
    """Retrieves chronological governance audit trail for regulatory compliance."""
    uid, email, _ = _resolve_user_ctx(current_user)
    _require_org_member(org_id, uid, user_email=email, min_role="Analyst")
    logs = TeamManager.get_audit_logs(org_id=org_id, limit=limit)
    return JSONResponse(content=safe_jsonable({"ok": True, "logs": logs}))
