"""
dataforge/api/schemas/teams.py
──────────────────────────────
Pydantic schemas for Team Workspaces, RBAC memberships, and Audit Logs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Organization team name")
    plan: Optional[str] = Field("Enterprise", description="Plan tier: Enterprise, Team, Starter")


class InviteMemberRequest(BaseModel):
    email: str = Field(..., description="Corporate email address of the invitee")
    name: Optional[str] = Field(None, description="Full name or display handle")
    role: str = Field("Analyst", description="Role: Admin, Analyst, Viewer")


class UpdateRoleRequest(BaseModel):
    new_role: str = Field(..., description="Target role: Admin, Analyst, Viewer")


class TeamMemberResponse(BaseModel):
    id: str
    org_id: str
    user_id: int
    user_email: str
    user_name: str
    role: str
    joined_at: str
    capabilities: List[str] = []


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    owner_id: int
    created_at: str
    my_role: Optional[str] = None
    member_count: Optional[int] = None


class AuditLogResponse(BaseModel):
    id: str
    org_id: str
    user_id: int
    user_email: str
    action: str
    target: str
    timestamp: str
    metadata: Dict[str, Any] = {}
