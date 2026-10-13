"""
dataforge/api/deps.py
──────────────────────
FastAPI dependency injection functions.

Every route uses these via Depends():
    current_user = Depends(get_current_user)
    upload_id    = Depends(get_upload_id)
    job_manager  = Depends(get_job_manager_dep)
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import Cookie, Depends, HTTPException, Query, Request, status

from dataforge.api.auth.jwt import get_user_id_from_token
from dataforge.api.config import get_settings
from dataforge.api.jobs.manager import JobManager, get_job_manager
from dataforge.api.repositories.upload import upload_repo
from dataforge.api.services.auth import auth_service
from dataforge.api.storage.manager import exists
from dataforge.api.websocket.manager import ConnectionManager, get_ws_manager
from dataforge.db import User

log = logging.getLogger(__name__)
settings = get_settings()


# ── Authentication ────────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
) -> User:
    """
    Extract and validate the JWT from the 'access_token' HTTP-only cookie
    or 'Authorization: Bearer <token>' header.
    Raises 401 if missing or invalid.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif access_token:
        token = access_token

    if token:
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            user = auth_service.get_user_by_id(user_id)
            if user is not None:
                request.state.user_id = user.id
                return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None),
) -> Optional[User]:
    """
    Extract and validate JWT if present (Bearer header or cookie), otherwise returns None.
    """
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif access_token:
        token = access_token

    if token:
        user_id = get_user_id_from_token(token)
        if user_id is not None:
            user = auth_service.get_user_by_id(user_id)
            if user is not None:
                request.state.user_id = user.id
                return user
    return None


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[Optional[User], Depends(get_optional_current_user)]


# ── Upload ID ─────────────────────────────────────────────────────────────────

async def get_upload_id(
    request: Request,
    upload_id: Optional[str] = Query(default=None),
) -> Optional[int]:
    """
    Extract upload_id from query string, JSON body, or form data.
    Does NOT validate ownership — use require_upload_access for that.
    """
    if upload_id is not None:
        return upload_id

    # Try JSON body
    try:
        body = await request.json()
        if isinstance(body, dict) and "upload_id" in body:
            return int(body["upload_id"])
    except Exception:
        pass

    # Try form data
    try:
        form = await request.form()
        if "upload_id" in form:
            return int(form["upload_id"])
    except Exception:
        pass

    return None


async def require_upload_access(
    upload_id: str,
    current_user: User,
    min_role: str = "Viewer",
    share_token: Optional[str] = None,
) -> dict:
    """
    Validate that the upload exists and the user has permission to access it.
    Supports Owner access, invited email collaborators, and share links (Google Sheets parity).
    Raises 401 if unauthenticated, 404 if not found, 403 on permission violation.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from dataforge.api.services.sharing import DatasetSharingService

    upload = upload_repo.get_by_id(upload_id)
    if not upload:
        from dataforge.api.storage.manager import STORE_DIR, exists, load
        meta = load(upload_id, "meta")
        if meta and isinstance(meta, dict):
            owner_id = meta.get("user_id")
            if owner_id == current_user.id:
                return meta
            # Check sharing permissions
            allowed, eff_role = DatasetSharingService.check_access(
                upload_id=upload_id,
                user=current_user,
                owner_id=owner_id,
                min_role=min_role,
                share_token=share_token,
            )
            if allowed:
                return meta
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: this dataset requires '{min_role}' permission (your access: '{eff_role}')",
            )

        t_dir = STORE_DIR / str(upload_id) / "tables"
        has_local_data = exists(upload_id, "df_raw") or exists(upload_id, "df_clean") or (t_dir.exists() and any(t_dir.glob("*.parquet")))
        if has_local_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: unverified dataset ownership",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found")

    owner_id = upload.get("user_id")
    if owner_id == current_user.id:
        return upload

    # Check collaborator / share link access
    allowed, eff_role = DatasetSharingService.check_access(
        upload_id=upload_id,
        user=current_user,
        owner_id=owner_id,
        min_role=min_role,
        share_token=share_token,
    )
    if allowed:
        return upload

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access denied: this dataset requires '{min_role}' permission (your access: '{eff_role}')",
    )


async def require_upload_with_data(
    upload_id: str,
    current_user: User,
    min_role: str = "Viewer",
    share_token: Optional[str] = None,
) -> dict:
    """
    Like require_upload_access but also checks that a dataset is loaded.
    """
    upload = await require_upload_access(upload_id, current_user, min_role=min_role, share_token=share_token)
    if not exists(upload_id, "df_raw") and not exists(upload_id, "df_clean"):
        from dataforge.api.storage.manager import load
        # Attempt to restore from Supabase if it exists there
        if load(upload_id, "df_raw") is None and load(upload_id, "df_clean") is None:
            print("DEBUG: deps 400 - No dataset loaded (load returned None)")
            raise HTTPException(
                status_code=400,
                detail="No dataset loaded. Please upload a file first.",
            )
    return upload


# ── Infrastructure singletons ─────────────────────────────────────────────────

def get_job_manager_dep() -> JobManager:
    return get_job_manager()


def get_ws_manager_dep() -> ConnectionManager:
    return get_ws_manager()


# ── Rate limiting (via slowapi) ───────────────────────────────────────────────

def get_remote_addr(request: Request) -> str:
    """Extract client IP for rate limiting (proxy-aware)."""
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
