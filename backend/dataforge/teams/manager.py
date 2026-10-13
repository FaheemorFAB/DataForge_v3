"""
dataforge/teams/manager.py
──────────────────────────
Enterprise Multi-Tenant Team Workspaces, Role-Based Access Control (RBAC),
and Governance Audit Logging Engine.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataforge.api.storage.manager import STORE_DIR

log = logging.getLogger(__name__)

# Role hierarchy: Admin (4) > Data Engineer (3) > Analyst (2) > Viewer (1)
ROLE_HIERARCHY: Dict[str, int] = {
    "Admin": 4,
    "Data Engineer": 3,
    "Analyst": 2,
    "Viewer": 1,
}

ROLE_CAPABILITIES: Dict[str, List[str]] = {
    "Admin": [
        "Manage Team & Billing",
        "Invite & Remove Members",
        "Role Assignment",
        "Production Model Deployment",
        "Database Connection Vault",
        "Full Data Ingestion & Joins",
        "AutoML & Pipeline Execution",
        "View All Workspaces & Audit Logs",
    ],
    "Data Engineer": [
        "Database Connection Vault",
        "Multi-Table Relational Joins",
        "Granular Cleaning & Preprocessing",
        "Pipeline Code Export",
        "AutoML Execution",
        "Model Registry Staging",
    ],
    "Analyst": [
        "Exploratory Data Analysis (EDA)",
        "AutoML Tournament Training",
        "Model Evaluation & Inference",
        "Dashboard & Report Authoring",
        "DuckDB SQL Analytics",
    ],
    "Viewer": [
        "Read-Only Workspace Access",
        "View Dashboards & Reports",
        "Inspect Model Leaderboards",
        "Export Visual Charts",
    ],
}

_LOCK = threading.Lock()


class TeamManager:
    """Manages multi-tenant organizations, team memberships, and audit trails."""

    @classmethod
    def _get_store_file(cls) -> Path:
        STORE_DIR.mkdir(parents=True, exist_ok=True)
        return STORE_DIR / "_teams_meta.json"

    @classmethod
    def _read_data(cls) -> Dict[str, Any]:
        p = cls._get_store_file()
        if not p.exists():
            return {"organizations": {}, "memberships": [], "audit_logs": []}
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("Failed to parse teams store, resetting: %s", e)
            return {"organizations": {}, "memberships": [], "audit_logs": []}

    @classmethod
    def _write_data(cls, data: Dict[str, Any]) -> None:
        p = cls._get_store_file()
        temp_file = p.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        temp_file.replace(p)

    @classmethod
    def ensure_default_team_for_user(
        cls, user_id: int, user_email: str, user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ensures a user has at least one default enterprise team workspace."""
        with _LOCK:
            data = cls._read_data()
            memberships = data.get("memberships", [])

            user_teams = [m for m in memberships if m.get("user_id") == user_id]
            if user_teams:
                org_id = user_teams[0]["org_id"]
                return data["organizations"].get(org_id, {})

            # Provision default organization
            org_id = f"org_{user_id}_{int(time.time())}"
            display_name = user_name or user_email.split("@")[0].title()
            org_name = f"{display_name}'s Enterprise Team"

            now_iso = datetime.now(timezone.utc).isoformat()
            org_record = {
                "id": org_id,
                "name": org_name,
                "slug": f"team-{user_id}",
                "plan": "Enterprise",
                "owner_id": user_id,
                "created_at": now_iso,
            }
            data.setdefault("organizations", {})[org_id] = org_record

            # Add user as Admin
            user_member = {
                "id": f"mem_{user_id}_{org_id}",
                "org_id": org_id,
                "user_id": user_id,
                "user_email": user_email,
                "user_name": user_name or user_email.split("@")[0],
                "role": "Admin",
                "joined_at": now_iso,
            }

            # Add seeded demo collaborators for team demonstration
            colleagues = [
                {
                    "id": f"mem_seed_1_{org_id}",
                    "org_id": org_id,
                    "user_id": 901,
                    "user_email": "sarah.chen@company.com",
                    "user_name": "Sarah Chen",
                    "role": "Data Engineer",
                    "joined_at": now_iso,
                },
                {
                    "id": f"mem_seed_2_{org_id}",
                    "org_id": org_id,
                    "user_id": 902,
                    "user_email": "marcus.vance@company.com",
                    "user_name": "Marcus Vance",
                    "role": "Analyst",
                    "joined_at": now_iso,
                },
                {
                    "id": f"mem_seed_3_{org_id}",
                    "org_id": org_id,
                    "user_id": 903,
                    "user_email": "elena.rostova@company.com",
                    "user_name": "Elena Rostova",
                    "role": "Viewer",
                    "joined_at": now_iso,
                },
            ]

            data.setdefault("memberships", []).extend([user_member, *colleagues])

            # Seed audit log
            audit_entry = {
                "id": f"aud_{int(time.time() * 1000)}",
                "org_id": org_id,
                "user_id": user_id,
                "user_email": user_email,
                "action": "CREATE_ORGANIZATION",
                "target": org_name,
                "timestamp": now_iso,
                "metadata": {"plan": "Enterprise", "initial_members": 4},
            }
            data.setdefault("audit_logs", []).append(audit_entry)

            cls._write_data(data)
            return org_record

    @classmethod
    def get_user_organizations(
        cls, user_id: int, user_email: str, user_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns all organizations the user belongs to, with their role."""
        cls.ensure_default_team_for_user(user_id, user_email, user_name)
        with _LOCK:
            data = cls._read_data()
            memberships = data.get("memberships", [])
            orgs_dict = data.get("organizations", {})

            result = []
            for m in memberships:
                if m.get("user_id") == user_id:
                    o_id = m.get("org_id")
                    if o_id in orgs_dict:
                        o_copy = dict(orgs_dict[o_id])
                        o_copy["my_role"] = m.get("role", "Viewer")
                        o_copy["my_joined_at"] = m.get("joined_at")
                        # Add member count
                        o_copy["member_count"] = sum(
                            1 for mem in memberships if mem.get("org_id") == o_id
                        )
                        result.append(o_copy)
            return result

    @classmethod
    def create_organization(
        cls,
        user_id: int,
        user_email: str,
        user_name: Optional[str],
        name: str,
        plan: str = "Enterprise",
    ) -> Dict[str, Any]:
        """Creates a new organization and assigns creator as Admin."""
        with _LOCK:
            data = cls._read_data()
            org_id = f"org_{int(time.time() * 1000)}"
            now_iso = datetime.now(timezone.utc).isoformat()

            org_record = {
                "id": org_id,
                "name": name.strip(),
                "slug": name.lower().replace(" ", "-"),
                "plan": plan,
                "owner_id": user_id,
                "created_at": now_iso,
            }
            data.setdefault("organizations", {})[org_id] = org_record

            member_record = {
                "id": f"mem_{user_id}_{org_id}",
                "org_id": org_id,
                "user_id": user_id,
                "user_email": user_email,
                "user_name": user_name or user_email.split("@")[0],
                "role": "Admin",
                "joined_at": now_iso,
            }
            data.setdefault("memberships", []).append(member_record)

            # Audit
            audit_entry = {
                "id": f"aud_{int(time.time() * 1000)}",
                "org_id": org_id,
                "user_id": user_id,
                "user_email": user_email,
                "action": "CREATE_ORGANIZATION",
                "target": name,
                "timestamp": now_iso,
                "metadata": {"plan": plan},
            }
            data.setdefault("audit_logs", []).append(audit_entry)

            cls._write_data(data)
            return org_record

    @classmethod
    def get_team_members(cls, org_id: str) -> List[Dict[str, Any]]:
        """Returns all members of an organization."""
        with _LOCK:
            data = cls._read_data()
            memberships = data.get("memberships", [])
            members = [m for m in memberships if m.get("org_id") == org_id]
            # Attach capability list to each role
            for m in members:
                m["capabilities"] = ROLE_CAPABILITIES.get(m.get("role", "Viewer"), [])
            return members

    @classmethod
    def invite_member(
        cls,
        org_id: str,
        inviter_id: int,
        inviter_email: str,
        email: str,
        name: Optional[str] = None,
        role: str = "Analyst",
    ) -> Dict[str, Any]:
        """Invites / adds a member to the organization with a specified role."""
        if role not in ROLE_HIERARCHY:
            raise ValueError(f"Invalid role '{role}'. Allowed: {list(ROLE_HIERARCHY.keys())}")

        with _LOCK:
            data = cls._read_data()
            memberships = data.get("memberships", [])

            # Check if user already in team
            for m in memberships:
                if m.get("org_id") == org_id and m.get("user_email") == email:
                    raise ValueError(f"User with email '{email}' is already in this team.")

            now_iso = datetime.now(timezone.utc).isoformat()
            new_user_id = int(time.time() * 1000) % 1_000_000
            new_member = {
                "id": f"mem_{new_user_id}_{org_id}",
                "org_id": org_id,
                "user_id": new_user_id,
                "user_email": email.strip(),
                "user_name": name or email.split("@")[0].title(),
                "role": role,
                "joined_at": now_iso,
            }
            memberships.append(new_member)

            # Audit
            audit_entry = {
                "id": f"aud_{int(time.time() * 1000)}",
                "org_id": org_id,
                "user_id": inviter_id,
                "user_email": inviter_email,
                "action": "INVITE_MEMBER",
                "target": email,
                "timestamp": now_iso,
                "metadata": {"role": role, "name": name},
            }
            data.setdefault("audit_logs", []).append(audit_entry)

            cls._write_data(data)
            new_member["capabilities"] = ROLE_CAPABILITIES.get(role, [])
            return new_member

    @classmethod
    def update_member_role(
        cls,
        org_id: str,
        modifier_id: int,
        modifier_email: str,
        target_user_id: int,
        new_role: str,
    ) -> Dict[str, Any]:
        """Updates a member's RBAC role."""
        if new_role not in ROLE_HIERARCHY:
            raise ValueError(f"Invalid role: {new_role}")

        with _LOCK:
            data = cls._read_data()
            memberships = data.get("memberships", [])

            updated = None
            for m in memberships:
                if m.get("org_id") == org_id and m.get("user_id") == target_user_id:
                    old_role = m.get("role")
                    m["role"] = new_role
                    updated = m
                    break

            if not updated:
                raise ValueError("Member not found in organization.")

            now_iso = datetime.now(timezone.utc).isoformat()
            audit_entry = {
                "id": f"aud_{int(time.time() * 1000)}",
                "org_id": org_id,
                "user_id": modifier_id,
                "user_email": modifier_email,
                "action": "UPDATE_ROLE",
                "target": updated["user_email"],
                "timestamp": now_iso,
                "metadata": {"old_role": old_role, "new_role": new_role},
            }
            data.setdefault("audit_logs", []).append(audit_entry)

            cls._write_data(data)
            updated["capabilities"] = ROLE_CAPABILITIES.get(new_role, [])
            return updated

    @classmethod
    def remove_member(
        cls,
        org_id: str,
        remover_id: int,
        remover_email: str,
        target_user_id: int,
    ) -> bool:
        """Removes a user from the organization."""
        with _LOCK:
            data = cls._read_data()
            memberships = data.get("memberships", [])

            target = None
            new_memberships = []
            for m in memberships:
                if m.get("org_id") == org_id and m.get("user_id") == target_user_id:
                    target = m
                else:
                    new_memberships.append(m)

            if not target:
                return False

            data["memberships"] = new_memberships
            now_iso = datetime.now(timezone.utc).isoformat()
            audit_entry = {
                "id": f"aud_{int(time.time() * 1000)}",
                "org_id": org_id,
                "user_id": remover_id,
                "user_email": remover_email,
                "action": "REMOVE_MEMBER",
                "target": target["user_email"],
                "timestamp": now_iso,
                "metadata": {"role": target["role"]},
            }
            data.setdefault("audit_logs", []).append(audit_entry)

            cls._write_data(data)
            return True

    @classmethod
    def record_audit(
        cls,
        org_id: str,
        user_id: int,
        user_email: str,
        action: str,
        target: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Records an arbitrary governance audit event."""
        with _LOCK:
            data = cls._read_data()
            now_iso = datetime.now(timezone.utc).isoformat()
            audit_entry = {
                "id": f"aud_{int(time.time() * 1000)}",
                "org_id": org_id,
                "user_id": user_id,
                "user_email": user_email,
                "action": action,
                "target": target,
                "timestamp": now_iso,
                "metadata": metadata or {},
            }
            data.setdefault("audit_logs", []).append(audit_entry)
            # Keep last 500 audit logs
            if len(data["audit_logs"]) > 500:
                data["audit_logs"] = data["audit_logs"][-500:]
            cls._write_data(data)

    @classmethod
    def get_audit_logs(cls, org_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent audit logs for an organization, newest first."""
        with _LOCK:
            data = cls._read_data()
            logs = [a for a in data.get("audit_logs", []) if a.get("org_id") == org_id]
            logs.reverse()
            return logs[:limit]

    @classmethod
    def get_user_role(cls, org_id: str, user_id: int) -> Optional[str]:
        """Returns the user's role in the organization, or None if not a member."""
        with _LOCK:
            data = cls._read_data()
            for m in data.get("memberships", []):
                if m.get("org_id") == org_id and m.get("user_id") == user_id:
                    return m.get("role")
            return None

