"""
dataforge/api/services/sharing.py
─────────────────────────────────
Google Sheets-style Dataset Sharing & User-Level Access Control Engine.
Supports email collaborator invitations, granular RBAC (Viewer, Analyst, Editor, Admin, Owner),
and configurable link sharing (Restricted vs Anyone with the link).
"""

from __future__ import annotations

import json
import logging
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dataforge.api.storage.manager import STORE_DIR
from dataforge.db import User

log = logging.getLogger(__name__)

# Numeric rank for comparison: Owner (5) > Admin (4) > Editor (3) > Analyst (2) > Viewer (1)
ROLE_RANKS: Dict[str, int] = {
    "Owner": 5,
    "Admin": 4,
    "Editor": 3,
    "Data Engineer": 3,
    "Analyst": 2,
    "Commenter": 2,
    "Viewer": 1,
}

_LOCK = threading.RLock()


class DatasetSharingService:
    """Manages granular dataset access permissions, collaborators, and share links."""

    @classmethod
    def _shares_path(cls, upload_id: str) -> Path:
        target_dir = STORE_DIR / str(upload_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / "_shares.json"

    @classmethod
    def get_shares(cls, upload_id: str, owner_id: Optional[int] = None, owner_email: Optional[str] = None) -> Dict[str, Any]:
        """Loads dataset sharing manifest, initializing default restricted settings if missing."""
        path = cls._shares_path(upload_id)
        with _LOCK:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if owner_id and not data.get("owner_id"):
                            data["owner_id"] = owner_id
                        if owner_email and not data.get("owner_email"):
                            data["owner_email"] = owner_email
                        return data
                except Exception as e:
                    log.warning("[sharing] Failed to read shares manifest for %s: %s", upload_id, e)

            # Initialize fresh manifest
            default_manifest: Dict[str, Any] = {
                "upload_id": str(upload_id),
                "owner_id": owner_id,
                "owner_email": owner_email or f"user_{owner_id or 'unknown'}@dataforge.app",
                "general_access": "restricted",  # "restricted" | "anyone_with_link"
                "link_role": "Viewer",           # "Viewer" | "Analyst" | "Editor"
                "share_token": f"sh_{secrets.token_urlsafe(16)}",
                "collaborators": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            try:
                temp_file = path.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(default_manifest, f, indent=2)
                temp_file.replace(path)
            except Exception as e:
                log.error("[sharing] Could not write default shares manifest for %s: %s", upload_id, e)

            return default_manifest

    @classmethod
    def _save_shares(cls, upload_id: str, manifest: Dict[str, Any]) -> None:
        path = cls._shares_path(upload_id)
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        temp_file = path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        temp_file.replace(path)

    @classmethod
    def check_access(
        cls,
        upload_id: str,
        user: Optional[User],
        owner_id: Optional[int] = None,
        min_role: str = "Viewer",
        share_token: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a user (or share token) meets min_role for a dataset.
        Returns: (allowed: bool, effective_role: str)
        """
        shares = cls.get_shares(upload_id, owner_id=owner_id)
        required_rank = ROLE_RANKS.get(min_role, 1)

        # 1. Owner check
        if user and shares.get("owner_id") == user.id:
            return True, "Owner"

        # 2. Direct email collaborator check
        if user and user.email:
            for member in shares.get("collaborators", []):
                if member.get("email", "").lower() == user.email.lower():
                    role = member.get("role", "Viewer")
                    if ROLE_RANKS.get(role, 1) >= required_rank:
                        return True, role
                    return False, role

        # 3. Share token match
        if share_token and share_token == shares.get("share_token"):
            link_role = shares.get("link_role", "Viewer")
            if ROLE_RANKS.get(link_role, 1) >= required_rank:
                return True, link_role
            return False, link_role

        # 4. General link access ("anyone_with_link")
        if shares.get("general_access") == "anyone_with_link":
            link_role = shares.get("link_role", "Viewer")
            if ROLE_RANKS.get(link_role, 1) >= required_rank:
                return True, link_role
            return False, link_role

        return False, "None"

    @classmethod
    def invite_collaborator(
        cls,
        upload_id: str,
        operator_id: int,
        email: str,
        role: str,
    ) -> Dict[str, Any]:
        """Adds or updates a collaborator by email. Operator must have Admin or Owner access."""
        with _LOCK:
            shares = cls.get_shares(upload_id)
            if shares.get("owner_id") != operator_id:
                # Check if operator is Admin
                op_role = next(
                    (m.get("role") for m in shares.get("collaborators", []) if m.get("user_id") == operator_id),
                    None,
                )
                if op_role not in ("Admin", "Owner"):
                    raise PermissionError("Only the Owner or Admin can manage dataset permissions.")

            cleaned_email = email.strip().lower()
            if not cleaned_email or "@" not in cleaned_email:
                raise ValueError("Invalid collaborator email address.")

            if role not in ROLE_RANKS:
                raise ValueError(f"Invalid role: {role}. Choose from: Viewer, Analyst, Editor, Admin.")

            # Prevent downgrading the owner
            if shares.get("owner_email", "").lower() == cleaned_email:
                raise ValueError("The dataset owner cannot be modified via collaborator invitations.")

            collaborators = shares.get("collaborators", [])
            existing = next((m for m in collaborators if m.get("email", "").lower() == cleaned_email), None)

            now_iso = datetime.now(timezone.utc).isoformat()
            if existing:
                existing["role"] = role
                existing["updated_at"] = now_iso
                existing["updated_by"] = operator_id
            else:
                collaborators.append({
                    "email": cleaned_email,
                    "role": role,
                    "invited_at": now_iso,
                    "invited_by": operator_id,
                })

            shares["collaborators"] = collaborators

            # Dispatch email invitation
            try:
                from dataforge.api.services.mailer import EmailDeliveryService
                from dataforge.db import db_get
                up_row = db_get("uploads", upload_id) or {}
                ds_name = up_row.get("filename") or f"Dataset {upload_id[:8]}"
                owner_label = shares.get("owner_email") or f"User #{operator_id}"
                share_token = shares.get("share_token")
                delivery = EmailDeliveryService.send_collaborator_invite(
                    recipient_email=cleaned_email,
                    role=role,
                    dataset_name=ds_name,
                    upload_id=upload_id,
                    inviter_name_or_email=owner_label,
                    share_token=share_token,
                )
                shares["last_delivery"] = delivery
            except Exception as e:
                log.warning("[sharing] Failed to dispatch invitation email to %s: %s", cleaned_email, e)

            cls._save_shares(upload_id, shares)
            return shares

    @classmethod
    def remove_collaborator(
        cls,
        upload_id: str,
        operator_id: int,
        email: str,
    ) -> Dict[str, Any]:
        """Removes a collaborator from the dataset."""
        with _LOCK:
            shares = cls.get_shares(upload_id)
            if shares.get("owner_id") != operator_id:
                op_role = next(
                    (m.get("role") for m in shares.get("collaborators", []) if m.get("user_id") == operator_id),
                    None,
                )
                if op_role not in ("Admin", "Owner"):
                    raise PermissionError("Only the Owner or Admin can remove collaborators.")

            cleaned_email = email.strip().lower()
            collaborators = [
                m for m in shares.get("collaborators", [])
                if m.get("email", "").lower() != cleaned_email
            ]
            shares["collaborators"] = collaborators
            cls._save_shares(upload_id, shares)
            return shares

    @classmethod
    def update_general_access(
        cls,
        upload_id: str,
        operator_id: int,
        general_access: str,
        link_role: str = "Viewer",
    ) -> Dict[str, Any]:
        """Updates link sharing mode ('restricted' | 'anyone_with_link') and default link role."""
        with _LOCK:
            shares = cls.get_shares(upload_id)
            if shares.get("owner_id") != operator_id:
                op_role = next(
                    (m.get("role") for m in shares.get("collaborators", []) if m.get("user_id") == operator_id),
                    None,
                )
                if op_role not in ("Admin", "Owner"):
                    raise PermissionError("Only the Owner or Admin can update general sharing settings.")

            if general_access not in ("restricted", "anyone_with_link"):
                raise ValueError("general_access must be 'restricted' or 'anyone_with_link'")

            if link_role not in ("Viewer", "Analyst", "Editor"):
                raise ValueError("link_role must be Viewer, Analyst, or Editor")

            shares["general_access"] = general_access
            shares["link_role"] = link_role
            cls._save_shares(upload_id, shares)
            return shares

    @classmethod
    def regenerate_share_token(cls, upload_id: str, operator_id: int) -> Dict[str, Any]:
        """Regenerates the secret share token, invalidating previous links."""
        with _LOCK:
            shares = cls.get_shares(upload_id)
            if shares.get("owner_id") != operator_id:
                raise PermissionError("Only the dataset Owner can regenerate share links.")

            shares["share_token"] = f"sh_{secrets.token_urlsafe(16)}"
            cls._save_shares(upload_id, shares)
            return shares
